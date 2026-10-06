FULL QUANTUM ENGINEERING LAB
============================

ROOT
  /mnt/deepa/quantum

IMPORTANT OPTIONAL / EXTERNAL REQUIREMENTS

1. CUDA-Q
   Installed in an isolated venv on a best-effort basis.
   GPU execution depends on compatible NVIDIA/CUDA support.
   CPU paths can still be tested independently.

2. SimCATS
   Source is downloaded.
   Current advertised Python support may not match Ubuntu 24.04 default Python.
   Do not force it into the main hardware venv.

3. QNPack
   Source is downloaded.
   NetSquid access requires separate credentials/account access.

4. QuISP
   Source is downloaded.
   Full simulator build requires OMNeT++.

5. MQT NAViz
   Source is downloaded.
   Full GUI build requires a sufficiently recent Rust toolchain.

6. Materials Project
   mp-api is installed.
   Remote Materials Project API queries require your own API key.

7. Cloud QPUs
   IBM/AWS/Azure/QPU credentials are not stored by this installer.

MAIN COMMANDS

  /mnt/deepa/quantum/quantum-manager.sh status
  /mnt/deepa/quantum/quantum-manager.sh roles
  /mnt/deepa/quantum/quantum-manager.sh gates
  /mnt/deepa/quantum/quantum-manager.sh test
  /mnt/deepa/quantum/quantum-manager.sh dashboard
  /mnt/deepa/quantum/quantum-manager.sh mlflow
  /mnt/deepa/quantum/quantum-manager.sh observability-up
  /mnt/deepa/quantum/quantum-manager.sh observability-down
  /mnt/deepa/quantum/quantum-manager.sh disk
  /mnt/deepa/quantum/quantum-manager.sh tree

