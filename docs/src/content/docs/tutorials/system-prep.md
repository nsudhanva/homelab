---
title: Talos Boot Media and Installer Image
description: Build the Talos installer image from the repo schematic with Longhorn storage extensions. Flash the ISO to USB and boot machines into maintenance mode.
keywords:
  - talos installer image
  - talos image factory
  - talos schematic
  - talos system extensions
  - talos maintenance mode
  - talos iso usb
  - longhorn iscsi talos
sidebar:
  order: 3
---

# Boot Media

Talos machines boot from an installer image built for this repo. The image carries the system extensions Longhorn needs, so storage works from the first boot with no follow-up package installation.

## Step 1: Review the schematic

The schematic lives in `talos/schematic.yaml` and pins the official extensions:

- `siderolabs/iscsi-tools` provides the iSCSI daemon and tools for persistent volume operations
- `siderolabs/util-linux-tools` provides trimming tools for volume maintenance

Bump extensions only by editing this file. The bootstrap script resolves the schematic to an installer image automatically.

## Step 2: Print the installer URLs

```bash
./scripts/talos-baremetal.sh iso-url
```

The script posts the schematic to the Image Factory and prints the installer container image and the bootable ISO URL for Talos `v1.14.0`. Both artifacts are deterministic for the pinned schematic and Talos version.

## Step 3: Flash the USB stick

Write the ISO to a USB stick with your usual flashing tool, then boot each machine from it.

## Step 4: Confirm maintenance mode

Each machine prints its IP addresses on the console and waits. From the workstation, confirm the machine answers over the API without credentials:

```bash
talosctl -n <machine-ip> version --insecure
```

If the machine is reachable, it is ready to receive its machine configuration in [Machine Configuration](./containerd.md).
