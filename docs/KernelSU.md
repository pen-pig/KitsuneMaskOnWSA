# Install KernelSU

## Install Manager

1. Download KernelSU Manager from [![Build Manager](https://github.com/tiann/KernelSU/actions/workflows/build-manager.yml/badge.svg?event=push)](https://github.com/tiann/KernelSU/actions/workflows/build-manager.yml?query=event%3Apush+is%3Acompleted+branch%3Amain) (Download the artifact named `manager`).

1. Unzip the downloaded zip package and get the manager apk named `KernelSU_vx.x.x-xx-.....apk`.

1. Use the command `adb install <apkname>.apk` to install the manager.

## Install Kernel

1. Download pre-build kernel from [![Build Kernel - WSA](https://github.com/tiann/KernelSU/actions/workflows/build-kernel-wsa.yml/badge.svg?event=push)](https://github.com/tiann/KernelSU/actions/workflows/build-kernel-wsa.yml?query=branch%3Amain+event%3Apush+is%3Acompleted) (Remember to download the same architecture).

1. Unzip the downloaded zip package and get the kernel file named `bzImage`.

1. Replace the kernel in the folder named `Tools` in the WSA directory with `bzImage`.

1. Restart WSA and then enjoy.

---

## SuKiSU-Ultra

SuKiSU-Ultra works the same way, the prebuilt WSA kernels are published at
<https://github.com/KernelSU-Next/KernelSU-Next/releases>. The manager is
available at <https://github.com/KernelSU-Next/KernelSU-Next/releases>.

When the build script is run with `--root-sol sukisu`, it picks the matching
`kernel-WSA-<abi>-<version>.zip` asset automatically.

## APatch

APatch does not ship prebuilt WSA kernels, so you have to provide one:

1. Build or obtain a WSA kernel with APatch support.
2. Pack it into a zip that contains the kernel image named `bzImage` (x64) or
   `Image` (arm64).
3. Put the zip into the `download` directory of this repository, named
   `apatch.zip` or `kernel-WSA-<abi>-<version>.zip`.
4. Run the build with `--root-sol apatch --arch arm64`.

APatch only supports the **ARM64** architecture.
