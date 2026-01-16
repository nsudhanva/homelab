---
title: Install Containerd
---

# Install Containerd

:::note

The `provision-*.yaml` playbooks run the `containerd` role, which installs containerd (upstream or apt), writes `/etc/containerd/config.toml`, and enables the service. Use this only if you are doing a manual setup.

:::

## Step 1: Install runc

```bash
sudo apt-get update
sudo apt-get install -y runc
```

## Step 2: Download containerd

```bash
CONTAINERD_VERSION=$(grep -E "containerd_version:" ansible/group_vars/all.yaml | head -n 1 | awk -F'\"' '{print $2}')
ARCH=$(uname -m)
if [ "${ARCH}" = "aarch64" ]; then CONTAINERD_ARCH=arm64; else CONTAINERD_ARCH=amd64; fi
curl -L --fail --remote-name-all https://github.com/containerd/containerd/releases/download/v${CONTAINERD_VERSION}/containerd-${CONTAINERD_VERSION}-linux-${CONTAINERD_ARCH}.tar.gz{,.sha256sum}
sha256sum --check containerd-${CONTAINERD_VERSION}-linux-${CONTAINERD_ARCH}.tar.gz.sha256sum
sudo tar xzvf containerd-${CONTAINERD_VERSION}-linux-${CONTAINERD_ARCH}.tar.gz -C /usr/local
rm containerd-${CONTAINERD_VERSION}-linux-${CONTAINERD_ARCH}.tar.gz containerd-${CONTAINERD_VERSION}-linux-${CONTAINERD_ARCH}.tar.gz.sha256sum
```

## Step 3: Install the systemd unit

```bash
cat <<EOF | sudo tee /etc/systemd/system/containerd.service
[Unit]
Description=containerd container runtime
Documentation=https://containerd.io
After=network.target local-fs.target

[Service]
ExecStart=/usr/local/bin/containerd
Type=notify
Delegate=yes
KillMode=process
Restart=always
RestartSec=5
LimitNOFILE=1048576
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity
OOMScoreAdjust=-999

[Install]
WantedBy=multi-user.target
EOF
```

## Step 4: Configure containerd

```bash
sudo mkdir -p /etc/containerd
/usr/local/bin/containerd config default | sudo tee /etc/containerd/config.toml > /dev/null
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml
sudo sed -i 's|sandbox_image = \"registry.k8s.io/pause:3.8\"|sandbox_image = \"registry.k8s.io/pause:3.10.1\"|g' /etc/containerd/config.toml
```

## Step 5: Enable and start containerd

```bash
sudo systemctl daemon-reload
sudo systemctl restart containerd
sudo systemctl enable containerd
```
