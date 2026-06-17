# Superbuild Version Lock

## Purpose

Define how XQ pins and builds external medical dependencies without letting system package drift control the application.

## Inputs

- Dependency role map.
- Medical image IO requirements.
- Modeling and meshing requirements.

## Outputs

- A pinned external dependency strategy.
- A rule for bundled/static or controlled shared builds.

## Code Ownership

Future files:

```text
externals/versions.cmake
externals/build-*.cmake
cmake/XQDependencies.cmake
```

## Rules

- One version per dependency family.
- One codec provider per codec family where possible.
- Prefer controlled superbuild outputs over arbitrary system libraries.
- External libraries must feed XQ-owned types, not appear in business-layer APIs.

## Version Decision Table

Fill this table during foundation hardening before source changes begin:

| Dependency | Required role | Version field | Build mode | Conflict check |
| --- | --- | --- | --- | --- |
| Qt6 | UI and event loop | `XQ_QT_VERSION=6.8.3` | shared | Qt plugins deploy from one Qt prefix |
| VTK | rendering and VTK XML IO | `XQ_VTK_VERSION=9.6.2` | shared or controlled static | one rendering backend, one zlib/libpng stack |
| ITK | image algorithms and medical image IO | `XQ_ITK_VERSION=5.4.6` | shared or controlled static | codec overlap with GDCM and system image libs |
| DCMTK | DICOM metadata and series scanning | `XQ_DCMTK_VERSION=3.6.8` | controlled static preferred | OpenSSL and zlib consistency |
| GDCM | DICOM pixel decode fallback | `XQ_GDCM_VERSION=3.0.10` | controlled static preferred | JPEG/JPEG2000 codec overlap |
| OpenCASCADE | modeling kernel | `XQ_OCCT_VERSION=7.9.3` | shared or controlled static | FreeType/TCL/TK optional features disabled unless required |
| MMG | mesh improvement | `XQ_MMG_VERSION=5.8.0` | controlled static preferred | compiler runtime consistency |
| tinyxml2 | XML project files | `XQ_TINYXML2_VERSION=11.0.0` | static | no duplicate exported target names |
| SQLite | local index | `XQ_SQLITE_VERSION=3.53.2` / `XQ_SQLITE_AMALGAMATION_VERSION=3530200` | static | single SQLite compile options |
| CharLS | JPEG-LS | `XQ_CHARLS_VERSION=2.4.4` | static | no duplicate JPEG-LS provider |
| OpenJPEG | JPEG 2000 | `XQ_OPENJPEG_VERSION=2.5.4` | static | no duplicate OpenJPEG provider |
| libjpeg-turbo | JPEG | `XQ_LIBJPEG_TURBO_VERSION=3.1.4.1` | static | no duplicate JPEG provider |
| libtiff | TIFF | `XQ_LIBTIFF_VERSION=4.7.1` | static | zlib/libjpeg provider consistency |
| zlib | compression for codecs | `XQ_ZLIB_VERSION=1.3.2` | static | one compression provider for codec stack |
| Eigen | geometry math | `XQ_EIGEN_VERSION=3.4.1` | header-only | no runtime conflict |

## Build Output Contract

The superbuild produces one dependency prefix:

```text
<xq-rebuild-workspace>/externals/install
```

The application build consumes only this prefix through:

```text
CMAKE_PREFIX_PATH=<xq-rebuild-workspace>/externals/install
```

System packages may be used only as bootstrap tools such as compiler, CMake, Ninja, Python for build scripts, and system linker tools.

## Implementation Contract

Future files:

```text
externals/CMakeLists.txt
externals/versions.cmake
externals/build-qt.cmake
externals/build-vtk.cmake
externals/build-itk.cmake
externals/build-dcmtk.cmake
externals/build-gdcm.cmake
externals/build-tinyxml2.cmake
externals/build-occt.cmake
externals/build-mmg.cmake
externals/build-codecs.cmake
externals/build-sqlite.cmake
externals/build-eigen.cmake
externals/check-version-lock.cmake
externals/fix-zlib-static-package.cmake
externals/check-zlib-static-package.cmake
externals/checks/vtk-package/CMakeLists.txt
cmake/check-controlled-dependency-boundary.cmake
cmake/XQDependencies.cmake
```

Each `build-*.cmake` file owns one dependency family and writes into the single controlled install prefix.

## Step Plan

- [x] Pin Qt6.
- [x] Pin VTK.
- [x] Pin ITK.
- [x] Pin DCMTK.
- [x] Pin GDCM.
- [x] Pin OpenCASCADE.
- [x] Pin MMG.
- [x] Pin tinyxml2.
- [x] Pin SQLite.
- [x] Pin CharLS, OpenJPEG, libjpeg-turbo, libtiff, and zlib.
- [x] Pin Eigen for math and transform code.
- [x] Record all version fields in `externals/versions.cmake`.
- [x] Generate one install prefix under `<xq-rebuild-workspace>/externals/install`.
- [x] Verify the first externals CMake configure generates under `<xq-rebuild-workspace>/build-externals`.
- [x] Verify CMake resolves tinyxml2 from the controlled prefix.
- [x] Verify VTK resolves from the controlled prefix when the 3D scene viewer contract starts.
- [x] Verify zlib exposes only the controlled static package files from the external prefix.
- [x] Verify Qt6 resolves from the controlled prefix when the Qt/VTK 3D scene viewer widget contract starts.
- [ ] Verify ITK, OpenCASCADE, MMG, SQLite, codec libraries, and Eigen resolve from the controlled prefix when their consuming feature implementation contracts start.

## Test Plan

Expected commands after the superbuild files exist:

```text
cmake -S <xq-rebuild-workspace>/externals -B <xq-rebuild-workspace>/build-externals -G Ninja
cmake --build <xq-rebuild-workspace>/build-externals --target xq_external_tinyxml2
cmake -S <xq-rebuild-workspace> -B <xq-rebuild-workspace>/build -G Ninja -DCMAKE_PREFIX_PATH=<xq-rebuild-workspace>/externals/install
ctest --test-dir <xq-rebuild-workspace>/build-externals -R XQControlledExternalsVersionLock --output-on-failure
ctest --test-dir <xq-rebuild-workspace>/build-externals -R XQControlledZlibStaticPackage --output-on-failure
ctest --test-dir <xq-rebuild-workspace>/build -R XQControlledDependencyBoundary --output-on-failure
```

Expected result:

all pinned dependency version fields exist in externals/versions.cmake
all controlled external build files exist
tinyxml2 package config resolves from <xq-rebuild-workspace>/externals/install
zlib package config exposes only the controlled static component from <xq-rebuild-workspace>/externals/install
the main application build does not use FetchContent for tinyxml2
VTK consumers resolve from <xq-rebuild-workspace>/externals/install after `XQ_BUILD_EXTERNAL_VTK=ON` and `xq_external_vtk` are run
VTK visualization-layer mask extraction/smoothing/decimation consumers resolve `FiltersCore` and `FiltersGeneral` from the controlled prefix
VTK volume-rendering consumers call `vtk_module_autoinit` so `RenderingVolumeOpenGL2` overrides are registered at runtime
Qt6 widget consumers resolve Core, Gui, Widgets, and OpenGLWidgets from <xq-rebuild-workspace>/externals/install after `XQ_BUILD_EXTERNAL_QT=ON` and `xq_external_qt` are run
VTK Qt widget consumers resolve `GUISupportQt`, `InteractionStyle`, and `InteractionWidgets` from <xq-rebuild-workspace>/externals/install after Qt6 and VTK are built from the controlled prefix
future ITK, OpenCASCADE, MMG, codec, SQLite, and Eigen consumers must resolve from <xq-rebuild-workspace>/externals/install after their OFF-by-default external targets are enabled and built

## Acceptance

- `externals/versions.cmake` contains exactly one version field for each required dependency.
- `cmake/XQDependencies.cmake` consumes the controlled prefix.
- Codec providers are not duplicated without a documented reason.
- No business-layer source file needs dependency-specific public types.
- No main-application `FetchContent` path remains for tinyxml2.

## Failure Repair

If two dependencies build separate copies of the same codec and produce link conflicts, repair this document and the exact external build file before touching XQ business code.

## Do Not Add

- Unpinned system-only dependency assumptions.
- Hidden fallback to random `/usr/lib` packages.
- Multiple codec copies without a documented reason.
