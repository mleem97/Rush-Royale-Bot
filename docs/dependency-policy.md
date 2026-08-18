# Dependency policy

RushBot targets the current stable Python 3.14 toolchain while keeping runtime dependencies explicit and reproducible.

The modernization branch currently contains provisional dependency declarations inherited from the bootstrap phase. Before the first runnable game-engine release, replace speculative exact minimums with ranges verified by a clean Linux and Windows install, generate a lock file for each supported platform, and verify wheel availability for Python 3.14.

Required gates:

1. create a clean virtual environment with Python 3.14;
2. install the project from `pyproject.toml` without using a pre-populated cache;
3. verify NumPy, OpenCV, Pillow and scikit-learn import successfully;
4. run the complete unit and replay suite;
5. produce an SBOM and dependency-license report;
6. reject packages without a compatible wheel unless a documented source-build path exists;
7. pin CI actions by immutable commit SHA for release branches;
8. update dependencies through reviewed automation rather than unrestricted `latest` resolution.

Heavy computer-vision and ML packages should move into optional extras so the ADB/device CLI remains installable without the training stack.
