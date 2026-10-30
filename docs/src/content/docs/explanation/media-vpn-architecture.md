---
title: Media VPN and Storage Architecture
description: Understanding how Gluetun, WireGuard, and Pod network namespaces enforce leak-free torrenting and hardlink storage on K3s.
keywords:
  - kubernetes vpn sidecar architecture
  - gluetun wireguard killswitch
  - qbittorrent pod network namespace
  - jellyfin media pvc hardlinks
  - linux kernel iptables routing table
sidebar:
  order: 7
---

# Media VPN and Storage Architecture

This document explains the security and storage architecture of the media automation stack.

```mermaid
flowchart TB
  subgraph Pod["Kubernetes Pod: qbittorrent (media namespace)"]
    subgraph NetNS["Shared Linux Network Namespace (netns)"]
      Loopback["lo (127.0.0.1)"]
      Eth0["eth0 (pod IP) - Cluster Pod Network"]
      Tun0["tun0 (WIREGUARD_ADDRESSES) - WireGuard Tunnel"]
    end

    Gluetun["Gluetun Container\n- Holds NET_ADMIN capability\n- Manages WireGuard crypto\n- Configures iptables killswitch"]
    Qbit["qBittorrent Container\n- Web UI listens on pod IP port 8080\n- Bound strictly to tun0\n- Zero-seeding policy"]
  end

  subgraph External["External Network"]
    WGServer["WireGuard Server Endpoint\n(WIREGUARD_ENDPOINT_IP:PORT, UDP)"]
    Swarm["BitTorrent Swarm Peers"]
    Gateway["Tailscale Gateway / Cluster DNS"]
  end

  Gluetun -- "Encrypted UDP only" --> Eth0 --> WGServer
  Qbit -- "All peer traffic" --> Tun0 --> Swarm
  Gateway -- "Port 8080 allowed" --> Eth0 --> Qbit
```

---

## Pod Network Namespace Sharing

In Kubernetes, all containers in a single Pod share one Linux network namespace (`netns`).

They share identical IP addresses, network interfaces, and kernel routing tables.

Containers communicate with each other over `127.0.0.1` (`localhost`) without network overhead.

In `apps/qbittorrent/deployment.yaml`, `gluetun` and `qbittorrent` run in the same Pod:

- `gluetun` creates and manages network interface `tun0`.
- `qbittorrent` sees interface `tun0` immediately in its local network stack.
- `qbittorrent` binds its peer sockets to the `tun0` address. That address comes from the `addresses` property of `kv/qbittorrent/vpn`, through `WIREGUARD_ADDRESSES`.
- The qBittorrent Web UI listens on port 8080 on the pod IP. Gluetun opens that port in its firewall with `FIREWALL_INPUT_PORTS=8080`, so the `qbittorrent` Service (port 80 to 8080) can reach it.

---

## Multi-Layer VPN Killswitch Protection

The stack uses three distinct layers to prevent network leaks.

```mermaid
flowchart TD
  App["Layer 1: qBittorrent Application Lock\n(Session\\Interface=tun0)"]
  Routing["Layer 2: Kernel Policy Routing\n(fwmark 0xca6c -> Table 51820)"]
  Firewall["Layer 3: Kernel Packet Filtering\n(iptables -P OUTPUT DROP)"]

  App --> Routing --> Firewall
```

### Layer 1: Application-Level Socket Binding

qBittorrent sets `Session\Interface=tun0` in `/config/qBittorrent/qBittorrent.conf`. This file lives on the `qbittorrent-config` PVC, not in Git. The [media automation guide](/how-to/media-automation/#step-4-configure-the-vpn-interface-lock) shows how to set it.

The BitTorrent engine binds its raw sockets strictly to the `tun0` address.

The application refuses to open peer sockets on interface `eth0`.

### Layer 2: Linux Kernel Policy Routing

Gluetun creates advanced policy routing rules in the kernel. The values below come from Gluetun at runtime, not from the manifests:

- Mark `0xca6c` identifies encrypted WireGuard traffic.
- Table `51820` directs all standard outbound traffic to device `tun0`.
- Table `199` directs internal cluster subnets (`10.42.0.0/16` and `10.43.0.0/16`) to `eth0`.

```text
0:     from all lookup local
99:    from all to 10.42.0.0/16 lookup 199
101:   not from all fwmark 0xca6c lookup 51820
32766: from all lookup main
```

### Layer 3: Kernel Firewall Killswitch (`iptables`)

The pod firewall sets default `DROP` policies on all chains:

- `-P INPUT DROP`
- `-P FORWARD DROP`
- `-P OUTPUT DROP`

The kernel allows outbound traffic on `eth0` for only two destinations:

- The WireGuard UDP endpoint (`WIREGUARD_ENDPOINT_IP` and `WIREGUARD_ENDPOINT_PORT`, from the `qbittorrent-vpn` Secret).
- Internal Kubernetes cluster subnets (`10.42.0.0/16` and `10.43.0.0/16`, from `FIREWALL_OUTBOUND_SUBNETS`).

Inbound traffic on `eth0` is allowed only on port 8080 (`FIREWALL_INPUT_PORTS`), for the Web UI.

The kernel drops all unencrypted outbound internet packets instantly.

---

## DNS Leak Prevention

DNS queries can expose activity if resolved outside the VPN.

Gluetun runs an embedded DNS resolver on `127.0.0.1:53`.

The container sets `/etc/resolv.conf` to `nameserver 127.0.0.1`.

All tracker and peer domain lookups route inside the encrypted `tun0` tunnel.

---

## Shared Storage and Hardlink Mechanics

Downloading and storing media requires efficient storage management.

Duplicating 50 GB video files wastes disk space and stresses solid-state drives.

The homelab uses one shared PersistentVolumeClaim named `jellyfin-media`. qBittorrent, Sonarr, Radarr, Bazarr, and Jellyfin mount it at `/media`. Filebrowser mounts it at `/srv`. Prowlarr and Seerr do not mount it:

```text
/media/
├── torrents/
│   ├── incomplete/
│   ├── movies/       <- qBittorrent writes completed file
│   └── tv/
├── movies/           <- Radarr creates hardlink
└── tv/               <- Sonarr creates hardlink
```

### How Hardlinks Operate

A hardlink points to the existing file inode on the same filesystem.

Both `/media/torrents/movies/video.mkv` and `/media/movies/Title/video.mkv` reference the same data blocks.

Creating a hardlink takes less than one millisecond and uses zero extra bytes.

When qBittorrent removes the torrent file, the video file remains intact in `/media/movies`.

```mermaid
flowchart LR
  Inode["File Inode 4892102\n(9.8 GB data blocks on NVMe)"]
  TorrentPath["/media/torrents/movies/filename.mkv"]
  JellyfinPath["/media/movies/Title (Year)/Title.mkv"]

  TorrentPath --> Inode
  JellyfinPath --> Inode
```

---

## Automated Notification Lifecycle

Real-time file monitoring (`inotify`) can miss events across container mount boundaries.

Radarr and Sonarr solve this problem through explicit REST API webhooks.

When an import completes, Radarr sends a notification to `http://jellyfin.media.svc:80`. The `jellyfin` Service forwards port 80 to container port 8096. You set up this connection in the Radarr and Sonarr UI, as the [media automation guide](/how-to/media-automation/#step-8-configure-jellyfin-library-scan-notifications) shows.

Jellyfin immediately starts an internal library scan on the specific movie directory.

This notification delivers new media to the user interface within five seconds.
