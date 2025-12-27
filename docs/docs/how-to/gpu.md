---
sidebar_position: 5
title: GPU Support
---

# GPU Support

## Step 1: Enable GPU support

### Intel GPU (iGPU for transcoding)

No host prerequisites needed - the Intel GPU Plugin DaemonSet handles everything.

The Intel GPU plugin manifest lives in `infrastructure/gpu/intel-plugin.yaml`.

Verify after deployment:

```bash
kubectl describe node | grep gpu.intel.com/i915
```

### NVIDIA GPU

#### Install NVIDIA Container Toolkit

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg --yes
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
```

#### Configure Containerd for NVIDIA

:::warning

These three commands are required for NVIDIA to work in Kubernetes.

:::

```bash
sudo nvidia-ctk runtime configure --runtime=containerd --set-as-default --cdi.enabled
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
sudo systemctl restart containerd
```

Verify after deployment:

```bash
kubectl describe node | grep nvidia.com/gpu
```

The NVIDIA GPU plugin manifest lives in `infrastructure/gpu/nvidia-plugin.yaml`.
