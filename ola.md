# install ola

first try to install from packages:
```bash
sudo apt install ola
```

if this does not work build it youself. 
you need to build it in a cross-compile enviroment - have a look at [`ola-pb2-crosscompile-handoff.md`](ola-pb2-crosscompile-handoff.md)


## compilation

based on https://github.com/OpenLightingProject/website/blob/f68f1b08d5046f34a0cf0ffc14db51c5d5a3f925/download_and_install/compiling_from_source.md

```bash
sudo apt install \  
    autoconf \
    automake \
    bison \
    flex \
    g++ \
    libavahi-client-dev \
    libcppunit-1.15- 0 \
    libcppunit-dev \
    libftdi-dev \
    libftdi1 \
    liblo-dev \
    libmicrohttpd-dev \
    libmicrohttpd12t64 \
    libncurses5-dev \
    libprotobuf-dev\
    libprotobuf-lite32t64 \
    libprotoc-dev \
    libtool \
    libusb-1.0-0-dev \
    make \
    pkg-config \
    protobuf-compiler \
    python3-numpy \
    python3-protobuf \
    uuid-dev \
    zlib1g-dev \
    python3-numpy \
    python3-protobuf
```

```bash
git clone https://github.com/OpenLightingProject/ola.git
```


```bash
nano ~/.bashrc
```
add
```bash
export LANGUAGE=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export LC_CTYPE=en_US.UTF-8
```


```bash
./configure \
    --enable-python-libs \
    --disable-doxygen-doc \
    --disable-all-plugins \
    --enable-e131 \
    --enable-dummy \
    --enable-osc \
    --enable-uartdmx
```

```bash
make -j$(nproc)
make check
sudo make install
```

```bash
sudo ldconfig
```
