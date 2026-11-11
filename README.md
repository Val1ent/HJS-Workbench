# HJS-Workbench

<!--
Language versions live in the collapsible sections below.
To add a language, copy one <details> block, change the summary to the native
language name, and translate the body. Keep technical identifiers, commands,
protocol names, units, and URLs in English. When the facts change, update every
language block together so the versions stay consistent.
-->

Select a language / 选择语言 / 選擇語言：

<details open>
<summary>English</summary>

# HJS-Workbench

A portable, cross-hardware digital debug workbench that combines **logic
analysis, signal generation, and measurement** in one shared core, delivered
through both a graphical application and a command-line interface.

The software is written to be hardware-independent. It talks to real boards
through a small backend interface, so the same core and the same two front-ends
can drive any device that provides a backend. The first fully supported device
is the WCH CH32H417; the Hardware support section below explains the current
scope and the reason it is documented this way.

## Architecture: one core, two front-ends

```
core/   shared, hardware-independent logic: capture, model, measurement,
         19 protocol decoders, UART decode, i18n, config, and the HAL
  cli/   command-line interface with its own version number
  gui/   PySide6 desktop application with its own version number
```

The CLI and the GUI are thin front-ends over the same core. They hold no
protocol or acquisition logic of their own, so a fix or a new decoder in the
core becomes available to both immediately. The two applications are released
independently and keep separate version numbers.

## Hardware support

The core never accesses a board directly. It works against a backend contract
(the hardware abstraction layer in `core/hal/`). Each backend declares its real
capabilities - channel count and names, supported sample rates, byte modes, and
baud rates. The GUI and CLI only present options the selected backend declares,
and reject configuration outside those capabilities rather than silently
guessing.

At the time of writing, **one real backend is implemented and verified on
physical hardware: the WCH CH32H417**. The reference firmware under
`firmware/` is therefore specific to that MCU. The software is designed for many
boards, but the supported list is deliberately limited to hardware that has
actually been built and tested, for the following reasons:

- **No simulated or mock devices.** The project does not bundle fake backends.
  A board is listed only after its backend is written against the official
  datasheet and exercised on the real device, so every "supported" claim can be
  trusted and reproduced.
- **Extending support does not touch the core.** Adding a board means adding a
  self-contained backend adapter and its declared capabilities. The existing
  CLI and GUI then drive the new board without any changes to their code.
- **Announcing support ahead of validation would be inaccurate.** Until a
  second board is physically available and verified, claiming broader
  compatibility would overstate what the project can do, so the documentation
  stays limited to the tested device.

The reference hardware below is the current backend, not a boundary of the
design. Additional backends are tracked on the roadmap and follow the same
datasheet-plus-physical-verification rule.

## Features

- **Graphical application** - capture, view waveforms, decode, and measure with
  the mouse (PySide6 + pyqtgraph); no terminal commands needed.
- **Command-line interface** - a unified menu for capture, live analysis, live
  measurement, protocol decoding, signal generation, and offline tools.
- **One-shot and continuous capture** - capture an exact number of points, or
  stream a rolling window that refreshes every 100-200 ms. The two modes share
  one data port and are mutually exclusive.
- **Multi-rate and burst capture** - on the CH32 High-Speed backend, select
  10 kHz, 100 kHz, 500 kHz, or 1 MHz, and choose realtime streaming or a
  712704-byte burst buffer; the rate and mode persist across sessions and fall
  back to the backend defaults when unsupported.
- **Waveform zoom controls** - Zoom in, Zoom out, and Fit buttons above the
  waveform plot, alongside the mouse wheel zoom and drag panning.
- **Multi-file import** - an Import action registers multiple `.sr`/`.bin`
  capture files in-app for switching between them; Remove drops only the
  in-app entry and never touches the file on disk.
- **Self-contained decoding** - 19 protocol decoders plus UART-to-text decoding
  directly in Python, with CSV logging; no external decoder application is
  required.
- **Signal generator** - a software-UART test message, square wave, PWM
  (frequency and duty), burst (frequency and pulse count), and forced high/low
  levels. Loop the generator output back to an input to capture and decode the
  device's own signal in a closed loop.
- **Real-time measurement** - frequency, period, high/low pulse width, duty,
  jitter (min/max), across channels.
- **Edge trigger and counting** - rising/falling edge detection and counting per
  channel.
- **Settings dialog** - language and light/dark theme preferences in one modal
  dialog (OK / Apply / Cancel), applied immediately without restarting; the
  toolbar is grouped into connection, acquisition, file, and settings areas.
- **Internationalization** - English, Français, Deutsch, 简体中文, and
  繁體中文. The language is chosen on the first run, remembered in the user
  config, and switchable at runtime. Decoder data, CSV headers, and sigrok
  metadata stay English in every language.
- **Onboarding** - a first-run step-by-step wizard that can be skipped and never
  reappears on its own, plus a re-openable Quick Start Guide in both front-ends.

The concrete channel count, sample rate, and generator pin listed in the
reference hardware section are the declared capabilities of the current CH32
backend. Other backends may report different values, and the applications adapt
to whatever the selected backend declares.

## Data path

```
GPIO sampling -> USB CDC bulk upload -> Python receive -> display / decode / log
```

## Reference hardware (current backend)

| Item | Spec |
|---|---|
| Board | MuseLab nanoCH32H417 (CH32H417QEU6) |
| Core | WCH QingKe V3F RISC-V, single core, 100 MHz |
| Inputs | 8 channels (PD0-PD7), selectable 10 kHz/100 kHz/500 kHz/1 MHz |
| Data ports | USB2.0 Full-Speed on the Type-C OTG port, or High-Speed 480 Mbps on the USB3 Type-A port |
| Burst buffer | 712704 bytes (696 KB), realtime and burst capture modes |
| Closed loop | PA15 (generator) wired back to PD0 (sampler) |

## Quick start

1. Flash a prebuilt firmware image from `firmware/` (for example
   `HJS-Workbench.hex`) with OpenOCD or the WCH toolchain via WCH-Link.
2. Connect **PA15 -> PD0** with a jumper wire for the closed-loop demo.
3. Run the graphical application (Python 3.12):

```bash
pip install -r gui/requirements.txt
python -m gui
```

The command-line interface covers the same functionality:

```bash
pip install pyserial
python -m cli    # menu 6 then 1 runs the 19/19 offline self-test
```

On the first GUI start a short onboarding wizard walks through connecting the
device, port selection, capture, waveform/decode/measurement, and the signal
generator. It can be skipped and reopened later via the Quick Start button (GUI)
or the Quick Start guide menu entry (CLI).

## Installation

Prebuilt installation paths exist for both editions:

- **Windows Setup (GUI)**: a single Setup executable that asks for the
  installer language first, then the install location, then installs the full
  GUI application with shortcuts and a registered uninstaller.
- **Terminal script (CLI)**: a one-line bash command for Ubuntu, WSL, and
  macOS that asks for language first, then the install directory, and
  downloads the matching platform binary. The default directory
  (`~/.local/bin`) needs no root.

Both flows ask for the language before any path or install prompt. The
installer language is its own; the installed application keeps its separate
in-app language setting. See [docs/INSTALL.md](docs/INSTALL.md) for the full
guide, the PATH note, and the build prerequisites.

## Protocol decoders

| Protocol | Decodes | Typical use |
|---|---|---|
| UART | start/data/stop bits -> characters | serial debug |
| NEC IR | address, command, repeat code | remote control |
| RC-5 IR | address, command, toggle bit | European remote |
| Servo PWM/PPM | pulse width, angle, multi-channel | RC / robotics |
| I2C (slow) | start/stop, address, data, ACK | sensors / OLED |
| SPI (slow) | CS, MOSI/MISO, CPOL/CPHA | memory / display |
| Stepper | steps, direction, speed, position | CNC / 3D printing |
| Quadrature encoder | 4x count, direction, RPM, index | motor loop / knob |
| HC-SR04 ultrasonic | echo time, distance | ranging / obstacle |
| Fan TACH | pulse interval, RPM | fan monitoring |
| DHT11 | start/response, 40 data bits, checksum, humidity, temperature | humidity / temperature |
| 1-Wire DS18B20 | reset/presence, ROM, scratchpad, CRC, temperature | temperature bus |
| SWD | line reset, ACK, register read/write with parity | debug port |
| Modbus RTU | address, function code, data, CRC-16 | RS-485 industrial bus |
| Wiegand | 26/34-bit frames, parity, card number | access control |
| HD44780 | 4-bit bus commands and characters | character LCD |
| Sony SIRC | address, command (12/15/20 bits) | IR remote |
| DS1302 | CE/SCLK/IO register reads and writes | real-time clock |
| Manchester | bit stream and bytes (IEEE 802.3 convention) | encoded links |
| NMEA 0183 | $...*XX sentences, checksum result | GPS |

> The default realtime rate is 10 kHz, and the High-Speed port adds up to
> 1 MHz capture for fast timing. I2C, SPI, and several decoders are still
> designed for slow signals; each decoder states its real hardware timing in
> its docstring.

## Repository layout

```
core/              shared core: capture I/O, data model, measurement, 19
                   decoders, UART decode, i18n, config, and the HAL
cli/               command-line interface (python -m cli)
gui/               graphical application (python -m gui), including the
                   continuous-capture worker, signal panel, and onboarding
assets/            application icon set and multi-size .ico
locales/           gettext catalogs: fr / de / zh_CN / zh_TW (.po sources + .mo)
scripts/           catalog compiler (compile_mo.py) and the CLI install
                   script (install.sh)
packaging/         PyInstaller spec files, Inno Setup script, build docs
examples/          sample .sr captures and a CSV log example
firmware/          prebuilt firmware images (.hex/.bin)
firmware/src/      firmware C source with a standalone Makefile
docs/              BOM, install guide, and documentation
```

## Build from source

The firmware source is in `firmware/src/`. With the WCH RISC-V toolchain (bundled
with MounRiver Studio) on the `PATH`:

```bash
cd firmware/src
make
```

The build produces `HJS-Workbench.elf`, `.hex`, and `.bin`. See
[firmware/src/BUILD.md](firmware/src/BUILD.md) for the full guide. The desktop
packages are built with PyInstaller; see [packaging/BUILD.md](packaging/BUILD.md).

## Roadmap

- **More real board backends** - additional HAL adapters, each backed by the
  official datasheet and physical-board measurements, never simulated data.
- **Universal protocol encoder** - multi-channel firmware output driven by
  timer, DMA, and GPIO hardware playback, with symmetric encode/decode in the
  core and closed-loop generate-capture-decode verification.
- **Native installers** - macOS and Linux installers alongside the Windows
  Setup; the cross-platform CLI install script becomes end-to-end on each
  platform once that platform's CLI binary is published.
- **Hardware** - more channels, higher sampling rates, faster upload, and a
  burst sampling architecture.

## License

Released under the **GNU General Public License v3.0 (GPL-3.0)**. See
[LICENSE](LICENSE).

</details>

<details>
<summary>简体中文</summary>

# HJS-Workbench

一款便携、跨硬件的数字调试工作台，把**逻辑分析、信号发生和测量**整合在
同一个共享核心中，并通过图形应用和命令行界面两种形态提供。

软件在设计上与硬件无关。它通过一个很小的后端接口与真实开发板通信，因此
同一个核心和两个前端可以驱动任何提供了后端的设备。第一个得到完整支持的
设备是 WCH CH32H417；当前支持范围以及这样说明的原因，见下方的硬件支持
部分。

## 架构：一个核心，两个前端

```
core/   共享、与硬件无关的逻辑：采集、数据模型、测量、19 个协议解码器、
         UART 解码、国际化、配置，以及硬件抽象层
  cli/   命令行界面，拥有独立版本号
  gui/   PySide6 桌面应用，拥有独立版本号
```

CLI 和 GUI 都是同一个核心之上的轻量前端，本身不包含任何协议或采集逻辑，
因此核心里的修复或新增解码器会立即对两者生效。两个应用独立发布，版本号
各自独立。

## 硬件支持

核心从不直接访问开发板，而是面向一个后端契约（即 `core/hal/` 中的硬件
抽象层）工作。每个后端声明自己的真实能力——通道数量和名称、支持的采样率、
字节模式和波特率。GUI 和 CLI 只展示所选后端声明的选项，对超出这些能力的
配置直接报错，而不是静默猜测。

截至目前，**只实现了一个真实后端，并在物理硬件上完成验证：WCH CH32H417**。
因此 `firmware/` 下的参考固件是针对该 MCU 的。软件本身为众多开发板而设计，
但支持列表被有意限定在已经实际构建和测试过的硬件上，原因如下：

- **不使用模拟或假设备。** 项目不内置虚假后端。一块板只有在对照官方数据
  手册写好后端、并在真实设备上验证之后才会被列入，因此每一个“支持”的说法
  都可信、可复现。
- **扩展支持不需要改动核心。** 增加一块板，只需新增一个自包含的后端适配
  器及其声明的能力。现有的 CLI 和 GUI 随后无需改动任何代码即可驱动新板。
- **在验证之前就宣称支持是不准确的。** 在第二块板实物到手并验证之前，声称
  更广泛的兼容性会夸大项目的实际能力，因此文档只写已测试的设备。

下方的参考硬件是当前后端，而不是设计的边界。更多后端已在路线图中规划，并
遵循同样的“数据手册加物理验证”规则。

## 功能特性

- **图形应用**——用鼠标即可采集、查看波形、解码和测量（PySide6 +
  pyqtgraph），无需终端命令。
- **命令行界面**——统一菜单，涵盖采集、实时分析、实时测量、协议解码、信号
  发生和离线工具。
- **单次与连续采集**——可采集精确点数，也可流式显示每 100-200 毫秒刷新的
  滚动窗口。两种模式共用一个数据端口，互斥使用。
- **多档采样与突发采集**——在 CH32 高速后端上可选 10 kHz、100 kHz、500 kHz
  或 1 MHz，并可选择实时流式或 712704 字节突发缓冲；速率和模式跨会话保存，
  不支持时自动回退到后端默认值。
- **波形缩放控件**——波形图上方提供放大、缩小和显示全部三个按钮，与鼠标滚轮
  缩放和拖拽平移并存。
- **多文件导入**——导入操作可在应用内登记多个 `.sr`/`.bin` 采集文件并随时
  切换；移除只删除应用内条目，绝不改动磁盘上的文件。
- **自包含解码**——19 个协议解码器加上直接在 Python 中完成的 UART 转文本
  解码，并支持 CSV 日志；无需外部解码软件。
- **信号发生器**——软件 UART 测试报文、方波、PWM（频率和占空比）、脉冲串
  （频率和脉冲数）以及强制高/低电平。把发生器输出接回某个输入，即可在闭环
  中采集并解码设备自己发出的信号。
- **实时测量**——跨通道的频率、周期、高/低脉冲宽度、占空比、抖动（最小/
  最大）。
- **边沿触发与计数**——逐通道的上升/下降沿检测和计数。
- **设置对话框**——语言和明暗主题偏好集中在一个模态对话框中（确定 / 应用 /
  取消），修改立即生效、无需重启；工具栏按连接、采集、文件和设置分区排列。
- **国际化**——English、Français、Deutsch、简体中文和繁體中文。语言在首次
  运行时选择，保存在用户配置中，并可在运行时切换。解码器数据、CSV 表头和
  sigrok 元数据在任何语言下都保持英文。
- **操作引导**——首次运行的分步向导，可跳过且不会自行再次出现；两个前端还
  提供可重新打开的快速入门指南。

参考硬件部分列出的具体通道数、采样率和发生器引脚，是当前 CH32 后端声明的
能力。其他后端可能报告不同的值，应用会适配所选后端声明的任何配置。

## 数据路径

```
GPIO 采样 -> USB CDC 批量上传 -> Python 接收 -> 显示 / 解码 / 记录
```

## 参考硬件（当前后端）

| 项目 | 规格 |
|---|---|
| 开发板 | MuseLab nanoCH32H417（CH32H417QEU6） |
| 内核 | WCH 青科 V3F RISC-V，单核，100 MHz |
| 输入 | 8 通道（PD0-PD7），可选 10 kHz/100 kHz/500 kHz/1 MHz |
| 数据端口 | Type-C OTG 口走 USB2.0 全速，USB3 Type-A 口走高速 480 Mbps |
| 突发缓冲 | 712704 字节（696 KB），支持实时与突发两种采集模式 |
| 闭环 | PA15（发生器）接回 PD0（采样器） |

## 快速开始

1. 用 OpenOCD 或 WCH 工具链通过 WCH-Link 烧录 `firmware/` 下的预构建固件
   镜像（例如 `HJS-Workbench.hex`）。
2. 用一根跳线连接 **PA15 -> PD0**，用于闭环演示。
3. 运行图形应用（Python 3.12）：

```bash
pip install -r gui/requirements.txt
python -m gui
```

命令行界面包含相同功能：

```bash
pip install pyserial
python -m cli    # 菜单 6 再选 1，运行 19/19 离线自测
```

GUI 首次启动时，会有简短的引导向导，依次介绍连接设备、端口选择、采集、
波形/解码/测量以及信号发生器。可以跳过，之后通过快速开始按钮（GUI）或快速
入门指南菜单项（CLI）重新打开。

## 安装

两个版本都有现成的安装途径：

- **Windows 安装程序（GUI）**：单个 Setup 可执行文件，先选择安装程序语言，
  再选择安装位置，然后安装完整 GUI 应用，并创建快捷方式、注册卸载程序。
- **终端脚本（CLI）**：适用于 Ubuntu、WSL 和 macOS 的一行 bash 命令，先选择
  语言，再选择安装目录，并下载对应平台的二进制文件。默认目录
  （`~/.local/bin`）无需 root 权限。

两种流程都在询问路径或安装位置之前先选择语言。安装程序语言只属于安装程序
本身；已安装的应用保留独立的程序内语言设置。完整指南、PATH 提示和构建前置
条件见 [docs/INSTALL.md](docs/INSTALL.md)。

## 协议解码器

| 协议 | 解码内容 | 典型用途 |
|---|---|---|
| UART | 起始/数据/停止位 -> 字符 | 串口调试 |
| NEC IR | 地址、命令、重复码 | 遥控器 |
| RC-5 IR | 地址、命令、翻转位 | 欧式遥控器 |
| Servo PWM/PPM | 脉宽、角度、多通道 | 航模 / 机器人 |
| I2C (slow) | 起始/停止、地址、数据、ACK | 传感器 / OLED |
| SPI (slow) | CS、MOSI/MISO、CPOL/CPHA | 存储器 / 显示屏 |
| Stepper | 步数、方向、速度、位置 | 数控 / 3D 打印 |
| Quadrature encoder | 4 倍计数、方向、转速、索引 | 电机闭环 / 旋钮 |
| HC-SR04 ultrasonic | 回波时间、距离 | 测距 / 避障 |
| Fan TACH | 脉冲间隔、转速 | 风扇监控 |
| DHT11 | 起始/响应、40 位数据、校验和、湿度、温度 | 湿度 / 温度 |
| 1-Wire DS18B20 | 复位/存在脉冲、ROM、暂存器、CRC、温度 | 温度总线 |
| SWD | 线路复位、ACK、带奇偶校验的寄存器读写 | 调试端口 |
| Modbus RTU | 地址、功能码、数据、CRC-16 | RS-485 工业总线 |
| Wiegand | 26/34 位帧、奇偶校验、卡号 | 门禁 |
| HD44780 | 4 位总线命令和字符 | 字符液晶 |
| Sony SIRC | 地址、命令（12/15/20 位） | 红外遥控 |
| DS1302 | CE/SCLK/IO 寄存器读写 | 实时时钟 |
| Manchester | 比特流和字节（IEEE 802.3 约定） | 编码链路 |
| NMEA 0183 | $...*XX 语句、校验和结果 | GPS |

> 默认实时速率为 10 kHz，高速端口最高支持 1 MHz 采集以捕捉快速时序。I2C、SPI
> 等若干解码器仍为慢速信号设计，每个解码器都在 docstring 中说明真实硬件时序。
> 每个解码器都在其 docstring 中说明真实的硬件时序。当加入采样率更高的后端
> 后，即可支持标准速率。

## 仓库布局

```
core/              共享核心：采集 I/O、数据模型、测量、19 个解码器、UART
                   解码、国际化、配置，以及硬件抽象层
cli/               命令行界面（python -m cli）
gui/               图形应用（python -m gui），包括连续采集工作线程、信号面板
                   和操作引导
assets/            应用图标集和多尺寸 .ico
locales/           gettext 目录：fr / de / zh_CN / zh_TW（.po 源文件 + .mo）
scripts/           目录编译器（compile_mo.py）与 CLI 安装脚本（install.sh）
packaging/         PyInstaller spec 文件、Inno Setup 脚本与构建文档
examples/          示例 .sr 采集文件和 CSV 日志示例
firmware/          预构建固件镜像（.hex/.bin）
firmware/src/      固件 C 源码，带独立 Makefile
docs/              BOM、安装指南与文档
```

## 从源码构建

固件源码位于 `firmware/src/`。将 WCH RISC-V 工具链（MounRiver Studio 自带）
加入 `PATH` 后：

```bash
cd firmware/src
make
```

构建会生成 `HJS-Workbench.elf`、`.hex` 和 `.bin`。完整指南见
[firmware/src/BUILD.md](firmware/src/BUILD.md)。桌面程序用 PyInstaller 构建，
见 [packaging/BUILD.md](packaging/BUILD.md)。

## 路线图

- **更多真实板后端**——新增硬件抽象层适配器，每个都有官方数据手册和板级
  测量支持，绝不使用模拟数据。
- **通用协议编码器**——由定时器、DMA 和 GPIO 硬件回放驱动的多通道固件输出，
  在核心中实现对称的编码/解码，并完成发生-采集-解码的闭环验证。
- **原生安装包**——在 Windows 安装程序之外，提供独立的 macOS 和 Linux 安装
  包；跨平台 CLI 安装脚本将在各平台 CLI 二进制文件发布后于该平台端到端可用。
- **硬件**——更多通道、更高采样率、更快上传，以及突发采样架构。

## 许可证

基于 **GNU 通用公共许可证 v3.0（GPL-3.0）** 发布。见 [LICENSE](LICENSE)。

</details>

<details>
<summary>繁體中文</summary>

# HJS-Workbench

一款可攜帶、跨硬體的數位除錯工作台，把**邏輯分析、訊號發生與量測**整合在
同一個共享核心中，並透過圖形應用與命令列介面兩種形式提供。

軟體在設計上與硬體無關。它透過一個精簡的後端介面與真實開發板通訊，因此
同一個核心與兩個前端可以驅動任何提供後端的裝置。第一個獲得完整支援的裝置
是 WCH CH32H417；目前的支援範圍以及如此說明的原因，見下方的硬體支援部分。

## 架構：一個核心，兩個前端

```
core/   共享、與硬體無關的邏輯：擷取、資料模型、量測、19 個協定解碼器、
         UART 解碼、國際化、設定，以及硬體抽象層
  cli/   命令列介面，擁有獨立版本號
  gui/   PySide6 桌面應用，擁有獨立版本號
```

CLI 與 GUI 都是同一個核心之上的輕量前端，本身不含任何協定或擷取邏輯，因此
核心裡的修復或新增解碼器會立即對兩者生效。兩個應用獨立發布，版本號各自
獨立。

## 硬體支援

核心從不直接存取開發板，而是面向一個後端合約（即 `core/hal/` 中的硬體抽象
層）運作。每個後端宣告自己的真實能力——通道數量與名稱、支援的取樣率、位元組
模式與鮑率。GUI 與 CLI 只呈現所選後端宣告的選項，對超出這些能力的設定直接
回報錯誤，而不是靜默猜測。

截至目前，**只實作了一個真實後端，並在實體硬體上完成驗證：WCH CH32H417**。
因此 `firmware/` 下的參考韌體是針對該 MCU 的。軟體本身為眾多開發板而設計，
但支援清單被刻意限定在已經實際建構與測試過的硬體上，原因如下：

- **不使用模擬或假裝置。** 專案不內建虛假後端。一塊板只有在對照官方資料
  手冊寫好後端、並在真實裝置上驗證之後才會被列入，因此每一個「支援」的說法
  都可信、可重現。
- **擴充支援不需更動核心。** 增加一塊板，只需新增一個自包含的後端介接器與
  其宣告的能力。現有的 CLI 與 GUI 隨後無需改動任何程式碼即可驅動新板。
- **在驗證之前就宣告支援並不準確。** 在第二塊板實物到手並驗證之前，聲稱更
  廣泛的相容性會誇大專案的實際能力，因此文件只寫已測試的裝置。

下方的參考硬體是目前後端，而非設計的邊界。更多後端已在路線圖中規劃，並遵循
同樣的「資料手冊加實體驗證」規則。

## 功能特性

- **圖形應用**——用滑鼠即可擷取、檢視波形、解碼與量測（PySide6 +
  pyqtgraph），無需終端命令。
- **命令列介面**——統一選單，涵蓋擷取、即時分析、即時量測、協定解碼、訊號
  發生與離線工具。
- **單次與連續擷取**——可擷取精確點數，也可串流顯示每 100-200 毫秒重新整理
  的捲動視窗。兩種模式共用一個資料埠，互斥使用。
- **多檔採樣與突發擷取**——在 CH32 高速後端上可選 10 kHz、100 kHz、500 kHz
  或 1 MHz，並可選擇即時串流或 712704 位元組突發緩衝；速率和模式跨會話儲存，
  不支援時自動回退到後端預設值。
- **波形縮放控制**——波形圖上方提供放大、縮小與顯示全部三個按鈕，與滑鼠滾輪
  縮放及拖曳平移並存。
- **多檔案匯入**——匯入操作可在應用程式內登記多個 `.sr`/`.bin` 擷取檔案並
  隨時切換；移除只刪除應用程式內條目，絕不改動磁碟上的檔案。
- **自包含解碼**——19 個協定解碼器加上直接在 Python 中完成的 UART 轉文字
  解碼，並支援 CSV 記錄；無需外部解碼軟體。
- **訊號產生器**——軟體 UART 測試訊息、方波、PWM（頻率與工作週期）、脈衝叢
  （頻率與脈衝數）以及強制高/低準位。把產生器輸出接回某個輸入，即可在閉迴路
  中擷取並解碼裝置自己發出的訊號。
- **即時量測**——跨通道的頻率、週期、高/低脈衝寬度、工作週期、抖動（最小/
  最大）。
- **邊緣觸發與計數**——逐通道的上升/下降邊緣偵測與計數。
- **設定對話方塊**——語言與明暗主題偏好集中在一個強制回應對話方塊中（確定 /
  套用 / 取消），變更立即生效、無需重新啟動；工具列按連接、擷取、檔案與設定
  分區排列。
- **國際化**——English、Français、Deutsch、簡體中文與繁體中文。語言在首次
  執行時選擇，保存在使用者設定中，並可在執行階段切換。解碼器資料、CSV 表頭
  與 sigrok 詮釋資料在任何語言下都保持英文。
- **操作引導**——首次執行的分步精靈，可略過且不會自行再次出現；兩個前端另
  提供可重新開啟的快速入門指南。

參考硬體部分列出的具體通道數、取樣率與產生器接腳，是目前 CH32 後端宣告的
能力。其他後端可能回報不同的值，應用會適配所選後端宣告的任何設定。

## 資料路徑

```
GPIO 取樣 -> USB CDC 大量上傳 -> Python 接收 -> 顯示 / 解碼 / 記錄
```

## 參考硬體（目前後端）

| 項目 | 規格 |
|---|---|
| 開發板 | MuseLab nanoCH32H417（CH32H417QEU6） |
| 核心 | WCH 青科 V3F RISC-V，單核心，100 MHz |
| 輸入 | 8 通道（PD0-PD7），可選 10 kHz/100 kHz/500 kHz/1 MHz |
| 資料埠 | Type-C OTG 埠走 USB2.0 全速，USB3 Type-A 埠走高速 480 Mbps |
| 突發緩衝 | 712704 位元組（696 KB），支援即時與突發兩種擷取模式 |
| 閉迴路 | PA15（產生器）接回 PD0（取樣器） |

## 快速開始

1. 用 OpenOCD 或 WCH 工具鏈透過 WCH-Link 燒錄 `firmware/` 下的預建韌體
   鏡像（例如 `HJS-Workbench.hex`）。
2. 用一條跳線連接 **PA15 -> PD0**，用於閉迴路展示。
3. 執行圖形應用（Python 3.12）：

```bash
pip install -r gui/requirements.txt
python -m gui
```

命令列介面包含相同功能：

```bash
pip install pyserial
python -m cli    # 選單 6 再選 1，執行 19/19 離線自測
```

GUI 首次啟動時，會有簡短的引導精靈，依序介紹連接裝置、連接埠選擇、擷取、
波形/解碼/量測以及訊號產生器。可以略過，之後透過快速開始按鈕（GUI）或快速
入門指南選單項（CLI）重新開啟。

## 安裝

兩個版本都有現成的安裝途徑：

- **Windows 安裝程式（GUI）**：單一 Setup 執行檔，先選擇安裝程式語言，再選擇
  安裝位置，然後安裝完整 GUI 應用程式，並建立捷徑、註冊解除安裝程式。
- **終端指令碼（CLI）**：適用於 Ubuntu、WSL 與 macOS 的一行 bash 指令，先選擇
  語言，再選擇安裝目錄，並下載對應平台的二進位檔。預設目錄（`~/.local/bin`）
  無需 root 權限。

兩種流程都在詢問路徑或安裝位置之前先選擇語言。安裝程式語言只屬於安裝程式
本身；已安裝的應用程式保留獨立的程式內語言設定。完整指南、PATH 提示與建置
前置條件見 [docs/INSTALL.md](docs/INSTALL.md)。

## 協定解碼器

| 協定 | 解碼內容 | 典型用途 |
|---|---|---|
| UART | 起始/資料/停止位 -> 字元 | 序列埠除錯 |
| NEC IR | 位址、命令、重複碼 | 遙控器 |
| RC-5 IR | 位址、命令、翻轉位 | 歐式遙控器 |
| Servo PWM/PPM | 脈衝寬、角度、多通道 | 航模 / 機器人 |
| I2C (slow) | 起始/停止、位址、資料、ACK | 感測器 / OLED |
| SPI (slow) | CS、MOSI/MISO、CPOL/CPHA | 記憶體 / 顯示器 |
| Stepper | 步數、方向、速度、位置 | 數控 / 3D 列印 |
| Quadrature encoder | 4 倍計數、方向、轉速、索引 | 馬達閉迴路 / 旋鈕 |
| HC-SR04 ultrasonic | 回波時間、距離 | 測距 / 避障 |
| Fan TACH | 脈衝間隔、轉速 | 風扇監控 |
| DHT11 | 起始/回應、40 位元資料、檢查碼、濕度、溫度 | 濕度 / 溫度 |
| 1-Wire DS18B20 | 重設/存在脈衝、ROM、暫存器、CRC、溫度 | 溫度匯流排 |
| SWD | 線路重設、ACK、帶同位檢查的暫存器讀寫 | 除錯埠 |
| Modbus RTU | 位址、功能碼、資料、CRC-16 | RS-485 工業匯流排 |
| Wiegand | 26/34 位元框、同位檢查、卡號 | 門禁 |
| HD44780 | 4 位元匯流排命令與字元 | 字元液晶 |
| Sony SIRC | 位址、命令（12/15/20 位元） | 紅外線遙控 |
| DS1302 | CE/SCLK/IO 暫存器讀寫 | 即時時鐘 |
| Manchester | 位元串流與位元組（IEEE 802.3 慣例） | 編碼鏈路 |
| NMEA 0183 | $...*XX 語句、檢查碼結果 | GPS |

> 預設即時速率為 10 kHz，高速埠最高支援 1 MHz 擷取以捕捉快速時序。I2C、SPI
> 等若干解碼器仍為慢速訊號設計，每個解碼器都在 docstring 中說明真實硬體時序。
> 每個解碼器都在其 docstring 中說明真實的硬體時序。當加入取樣率更高的後端
> 後，即可支援標準速率。

## 倉庫布局

```
core/              共享核心：擷取 I/O、資料模型、量測、19 個解碼器、UART
                   解碼、國際化、設定，以及硬體抽象層
cli/               命令列介面（python -m cli）
gui/               圖形應用（python -m gui），包括連續擷取工作執行緒、訊號
                   面板與操作引導
assets/            應用圖示集與多尺寸 .ico
locales/           gettext 目錄：fr / de / zh_CN / zh_TW（.po 來源檔案 + .mo）
scripts/           目錄編譯器（compile_mo.py）與 CLI 安裝腳本（install.sh）
packaging/         PyInstaller spec 檔案、Inno Setup 腳本與建構文件
examples/          範例 .sr 擷取檔與 CSV 記錄範例
firmware/          預建韌體鏡像（.hex/.bin）
firmware/src/      韌體 C 原始碼，帶獨立 Makefile
docs/              BOM、安裝指南與文件
```

## 從原始碼建構

韌體原始碼位於 `firmware/src/`。將 WCH RISC-V 工具鏈（MounRiver Studio 內建）
加入 `PATH` 後：

```bash
cd firmware/src
make
```

建構會產生 `HJS-Workbench.elf`、`.hex` 與 `.bin`。完整指南見
[firmware/src/BUILD.md](firmware/src/BUILD.md)。桌面程式用 PyInstaller 建構，
見 [packaging/BUILD.md](packaging/BUILD.md)。

## 路線圖

- **更多真實板後端**——新增硬體抽象層介接器，每個都有官方資料手冊與板級
  量測支援，絕不使用模擬資料。
- **通用協定編碼器**——由計時器、DMA 與 GPIO 硬體回放驅動的多通道韌體輸出，
  在核心中實作對稱的編碼/解碼，並完成發生-擷取-解碼的閉迴路驗證。
- **原生安裝套件**——在 Windows 安裝程式之外，提供獨立的 macOS 與 Linux 安裝
  套件；跨平台 CLI 安裝腳本將在各平台 CLI 二進位檔發布後於該平台端到端可用。
- **硬體**——更多通道、更高取樣率、更快上傳，以及突發取樣架構。

## 授權條款

基於 **GNU 通用公共授權條款 v3.0（GPL-3.0）** 發布。見 [LICENSE](LICENSE)。

</details>
