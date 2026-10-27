# Daniel's drivers course, taught on his own KeyLab, and the three-position driver toggle design (2026-10-27)

Workflow run wf_61110fb3-a0b (task wpc25jaw9), run one agent at a time to spare memory. Daniel's words (verbatim): "can we also make the driver be toggleable so we can have our custom one and the native one for firmware updates? also I liked your userspace "driver" idea, but this also seems like a lot of fun and I want to learn more about how drivers work in general, this has been something ive been really wanting to learn". Four stages: the concept track (with hardware analogies, predict-before-you-look questions and teach-back prompts), the machine walk (his own PC's driver stack, read-only), the toggle design (Arturia/Thesycon, Microsoft's class drivers, WinUSB + our user-mode driver), and the assembled course. Everything was read-only: no driver was switched, nothing installed, the KeyLab's ports never opened. Verbatim; local paths shortened.

Vandor's read: the course is the deliverable Daniel reads (it is also published as a page); the toggle design is design only, and its first experiment (position 1 -> 2 -> 1) is done by hand with Daniel present. Notable finds along the way: both Microsoft MIDI class drivers are already in the driver store (usbmidi2 has never been bound here); Arturia's INF writes DFUProtocol = 2, so firmware updates plausibly need its driver; Secure Boot is on, so a kernel driver of our own would need Microsoft's signature; the PC has two past blue screens (0x9F/3 on 2026-10-21, a device holding a power request too long; 0x133/0 on 2026-08-20, a DPC or ISR over its time budget) whose minidumps have not been read yet.

---

## The assembled course (verbatim)

# Daniel's Drivers Course: how drivers work, taught on your own KeyLab (2026-10-27)

On 2026-10-27 you asked, in your words: "can we also make the driver be toggleable so we can have our custom one and the native one for firmware updates? also I liked your userspace "driver" idea, but this also seems like a lot of fun and I want to learn more about how drivers work in general, this has been something ive been really wanting to learn".

This document answers both questions. It teaches how drivers work using only the machine in front of you, and its final lab is the toggle. Each chapter fits one Forest Walk and follows the same steps:
1. the idea in plain words;
2. a hardware analogy;
3. the deeper level, marked whenever it goes deep;
4. a prediction you write down before looking;
5. a stop on your own PC where you look;
6. the answer;
7. a teach-back to close;
8. one line on what the chapter unlocks in the lab.

**How claims are graded**
- **[S]** a cited source says it. "Fetched" means one of the lanes read that page on 2026-10-26 or 2026-10-27. Anything else is cited from a standard reference.
- **[S:local]** measured read-only on this PC on 2026-10-27.
- **[I]** my inference.

**Safety rule for every Look.** Every command in the chapters only lists or reads. None of them opens the KeyLab's MIDI ports or its USB handle, none changes a driver, and none needs FL closed. Run them in an ordinary PowerShell window. Only the capstone lab changes anything, and each of those steps waits for your go.

---

## Page 1: the map

### The toggle question, answered in five points

1. **Yes, it can be built, and Windows already has the switch.** Every driver package sits on this PC at the same time, and only one drives the KeyLab at any moment. Run `pnputil /enum-devices /instanceid "USB\VID_1C75&PID_02CE\7656400341020110" /drivers` and it lists two candidates for the KeyLab [S:local]:
   - Arturia's driver, marked "Best Ranked / Installed";
   - Windows' "USB Composite Device", marked "Outranked".
2. **There are three positions.**
   - **1. Arturia's driver** (really Thesycon's TUSBAudio). This is home, and firmware updates happen here.
   - **2. Microsoft's built-in class driver.** Already on the PC; nothing to download.
   - **3. Microsoft's signed WinUSB driver plus a program of ours.** That program is the userspace driver.
3. **The positions form a star, like DualBIOS on your AORUS board.** Every move starts from home and comes back to it, and any failure lands at home.
4. **No kernel code of ours runs in any position,** so Secure Boot is never touched.
5. **The first experiment is 1 → 2 → 1, by hand in Device Manager, with you present.** It takes about 40 minutes, downloads nothing, and every step can be undone.

### The KeyLab's family tree, as measured [S:local]

```
Ryzen 9 9950X3D, PCIe root port GPP7 (bus 0, device 2, function 1)          driver: pci
 └ chipset PCIe switch: upstream port 1022:43F4 → downstream port 1022:43F5    driver: pci
   └ AMD USB 3.20 xHCI controller 1022:43FD                                    USBXHCI (framework-built, + UCX)
     └ USB Root Hub (USB 3.0)                                                  USBHUB3 (framework-built)
       └ port 8: KeyLab 88 mk3   USB\VID_1C75&PID_02CE\7656400341020110          arturiausbmidi (Thesycon, hand-built WDM)   oem22.inf
         └ TUSBAUDIO_ENUM\VID_1C75&PID_02CE&KS\…  (a child node Thesycon invents)   ksthunk + arturiausbmidiks (AVStream)   oem11.inf
           ├ the Windows MIDI Services endpoint  SWD\MIDISRV\MIDIU_KSA_16201702556534547415   (no driver; midisrv publishes it)
           └ four WinMM port nodes: "KeyLab 88 mk3 MIDI" and "KeyLab 88 mk3 DAW", in and out
user mode:  FL → winmm.dll → wdmaud2.drv → midisrv.exe → the KS child above
```

### The route through the course

| Ch | Title | The question it answers | Your stop on the machine | Depth | What it unlocks in the lab |
|---|---|---|---|---|---|
| 0 | The family tree | Where does the KeyLab live? | Walk from port 8 up to the CPU | light | Which node the toggle acts on |
| 1 | What a driver is | Why does Windows need one? | Kernel driver vs service vs DLL | light | The three positions are three translators |
| 2 | User mode and kernel mode | Why is a kernel bug a blue screen? | Your two real blue screens; midisrv's uptime | **deep** (IRQL) | Why position 3 keeps our code out of the kernel |
| 3 | How a request travels | What happens between "write" and the wire? | Driver stacks on five nodes | **deep, matters** | Only the top layer changes per position |
| 4 | Interrupts, DMA, polling | Who taps whom on the shoulder? | The USB controller's registers and 8 interrupt vectors | **deep** (optional) | Why a stuck write is silent |
| 5 | How Windows picks a driver | Who wins, and why? | The scoreboard | **deep, matters most** | "Go home" means letting the scoreboard choose |
| 6 | Packages and signing | Who vouches for a driver? | Signer, catalog, Secure Boot | **deep, matters** | Why option 3a needs no trust change and 3b does |
| 7 | WDM, KMDF, UMDF | How are drivers built? | Search six driver files for the framework | light | Which positions run framework code |
| 8 | USB from the wire up | What did the KeyLab tell Windows? | IDs, capabilities, OS-descriptor flag | **deep** (optional) | The `MI_xx` children in position 2 |
| 9 | USB-MIDI 1.0 | What do the bytes look like on USB? | Pack your own LED message | **deep, and fun** | What our program must do in position 3 |
| 10 | The Windows MIDI stack | How does FL reach the KeyLab? | KS pins, the endpoint, the port names | medium | What changes for FL in each position |
| 11 | Userspace drivers | Can a program be the driver? | WinUSB in the store; the door already open | medium | Position 3 |
| Lab | The toggle | — | 1 → 2 → 1 by hand | — | — |

### Corrections made while assembling the course (read these before chapter 5)

1. **INF numbers.** The brief said oem41. On this PC Arturia's main package is **oem22.inf** (`arturiausbmidi.inf`) and its KS child package is **oem11.inf** (`arturiausbmidiks.inf`) [S:local]. Windows reuses these numbers, so any tool must find packages by their original names [S:local, setupapi log].
2. **Chapter 5 has a disputed prediction, left open on purpose.** If Arturia's driver steps aside, which Microsoft driver takes the MIDI part?
   - The curriculum said USBMidi2.
   - The machine walk argues for the older usbaudio.sys, and shows local precedent.

   The lab's first question settles it with Windows' own numbers.
3. **USBView and the classic WinDbg are already on this PC** (found during assembly) [S:local]. Two items that looked like downloads are now only approvals to run something.
4. **Chapter 1's answer gains two hidden helpers.** The USB controller extension (Ucx01000) and the KMDF framework runtime (Wdf01000) both run without ever appearing as a layer in a stack [S:local].
5. **midisrv has run continuously since 2026-10-22 03:18:55** [S:local], through the 10-26 hang and your power cycle. Only the device nodes were rebuilt.

---

## Chapter 0: The family tree

**The idea.** Windows keeps every device in one tree, the device tree. Each entry is a *device node*, and a node's parent is whatever it is plugged into. Windows chooses a driver for each node separately. So before learning what drivers do, find where the KeyLab's nodes sit.

**The analogy.** This is HWiNFO's bus view, or `lspci -t` on Linux. PCIe is a tree of root ports, switches and endpoints. One of those endpoints is the USB controller (the xHCI), which hosts a second tree of hubs and ports. The KeyLab's path crosses both trees.

**Predict before you look.** How many hops separate the CPU from the keyboard? Does the KeyLab ride the CPU's own USB, or the chipset's?

**Machine stop 0: walk the tree.**
- **Look:**
  ```
  $id='USB\VID_1C75&PID_02CE\7656400341020110'; while($id -notlike 'HTREE*'){ $d=Get-PnpDevice -InstanceId $id; '{0} [{1}] {2}' -f $d.FriendlyName,$d.Service,$id; $id=(Get-PnpDeviceProperty -InstanceId $id -KeyName DEVPKEY_Device_Parent).Data }
  ```
  then
  ```
  pnputil /enum-devicetree "USB\VID_1C75&PID_02CE\7656400341020110" /stack /drivers
  ```
  and the address:
  ```
  Get-PnpDeviceProperty -InstanceId 'USB\VID_1C75&PID_02CE\7656400341020110' -KeyName DEVPKEY_Device_LocationPaths | Select-Object -ExpandProperty Data
  ```
- **Printed today** [S:local]:
  ```
  ACPI x64-based PC                          ROOT\ACPI_HAL\0000
   └ Microsoft ACPI-Compliant System         ACPI_HAL\PNP0C08\0
     └ PCI Express Root Complex              ACPI\PNP0A08\0
       └ PCI Express Root Port  1022:14DB    PCI 0:2.1, ACPI GPP7          stack pci | ACPI | pci
         └ PCI Express Upstream Switch Port 1022:43F4  bus 7 (UP00)         stack pci | ACPI | pci
           └ PCI Express Downstream Switch Port 1022:43F5 bus 8 dev 12 (DP60), one of 7
             └ AMD USB 3.20 eXtensible Host Controller - 1.10 (Microsoft) 1022:43FD bus 23 (XH00)
               │                                                            stack USBXHCI | ACPI | pci
               └ USB Root Hub (USB 3.0)  USB\ROOT_HUB30\7&397afaa3&0&0      stack USBHUB3 | ACPI | USBXHCI
                 ├ port 7:  Generic USB Hub 1A40:0101
                 ├ port 11: USB Composite Device 048D:5711 "GIGABYTE Device " (usbccgp)
                 └ port 8:  KeyLab 88 mk3  USB\VID_1C75&PID_02CE\7656400341020110
                     │                                           stack arturiausbmidi | ACPI | USBHUB3   (oem22.inf)
                     └ KeyLab 88 mk3  TUSBAUDIO_ENUM\VID_1C75&PID_02CE&KS\7656400341020110
                         │                                       stack ksthunk | arturiausbmidiks | arturiausbmidi (oem11.inf)
                         ├ KeyLab 88 mk3 (MIDI Endpoint)  SWD\MIDISRV\MIDIU_KSA_16201702556534547415   (c_midi.inf, no driver)
                         ├ KeyLab 88 mk3 MIDI  SWD\MMDEVAPI\…_0_0   input
                         ├ KeyLab 88 mk3 DAW   SWD\MMDEVAPI\…_0_1   input
                         ├ KeyLab 88 mk3 MIDI  SWD\MMDEVAPI\…_1_0   output
                         └ KeyLab 88 mk3 DAW   SWD\MMDEVAPI\…_1_1   output
  ```
  The location paths are `PCIROOT(0)#PCI(0201)#PCI(0000)#PCI(0C00)#PCI(0000)#USBROOT(0)#USB(8)` and `ACPI(_SB_)#ACPI(PCI0)#ACPI(GPP7)#ACPI(UP00)#ACPI(DP60)#ACPI(XH00)#ACPI(RHUB)#ACPI(POT8)`.
- **What it means:**
  - Read the PCI path left to right: the CPU's root complex → root port 02.1 → the chipset's upstream port → its downstream port 0C → the xHCI controller → the root hub → port 8.
  - The board is a Gigabyte X870E AORUS MASTER with **two chipset chips**. X870E boards chain two of AMD's Promontory 21 chips in a row [I]. A second `1022:43FD` USB controller sits behind the first chip's downstream port 08.0 [S:local].
  - The KeyLab hangs off **the first chip, the one closest to the CPU**. It is not on the CPU's own USB controllers (1022:15B6, 15B7 and 15B8) [S:local].
  - The same root hub also carries a USB 2.0 hub (port 7) and Gigabyte's RGB controller (port 11) [S:local].

**The answer.** From the CPU's root port it takes three PCIe hops (switch upstream port, downstream port, xHCI), then the root hub, then port 8. The keyboard goes through the chipset's PCIe uplink, not through the CPU's own USB [S:local; I]. None of this matters for MIDI bandwidth [I].

**Teach-back.** Point to the node where a toggle would act, and say why it is not the KS child. *(It is the USB node on port 8, because Arturia's driver claims the whole device there. The KS child exists only because Arturia's driver created it.)*

**For the lab.** Every position changes only what sits on the port-8 node and below it. Everything above port 8 stays exactly as it is.

---

## Chapter 1: What a driver is, and why Windows needs one

**The idea.** Windows speaks a few generic verbs: open, read, write and "do this special thing". Every device speaks its own dialect. A driver translates between the two. It also tells Windows what the device is, how to power it, and what to do when it disappears. Without a driver, Windows knows only that "something with vendor 1C75 and product 02CE is on port 8", and can do nothing with it.

**The analogy.** AMD's "FineWine". The same Navi silicon got faster with driver updates, because the GPU driver is the compiler and scheduler between DirectX or Vulkan and the GPU's own command format. The API is the contract apps see, the ISA is the silicon's language, and the driver translates. For the KeyLab:
- the contract is "a MIDI port";
- the silicon's language is USB-MIDI packets plus Arturia's SysEx;
- the translator is Thesycon's TUSBAudio under an Arturia label.

**The deeper level.**
- A Windows driver is a kernel module: a `.sys` file, which is an ordinary executable image. It is registered as a service of type 1 and attached as one layer of a device's stack [S: L15, B1].
- A driver has three jobs: moving data (I/O), Plug and Play (start, stop, remove) and power [S: B1].
- Not every driver touches hardware. `ksthunk` is a pure software filter that sits on every media-class device [S:local: the MEDIA class's `UpperFilters=ksthunk`].
- The word "driver" is overloaded. `wdmaud2.drv` is a user-mode DLL that runs inside each app [S:local].

**Predict before you look.** How many kernel drivers, ones you could name, sit between a Python LED write and the USB cable?

**Machine stop 1: what kind of thing is each name?**
- **Look 1a:** kernel driver or service?
  ```
  Get-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Services\midisrv, HKLM:\SYSTEM\CurrentControlSet\Services\arturiausbmidi | Select-Object PSChildName,Type,Start,ImagePath
  ```
- **Printed today** [S:local]:

  | Name | Type | Start | ImagePath |
  |---|---|---|---|
  | `arturiausbmidi` | 1 | 3 | `…\DriverStore\FileRepository\arturiausbmidi.inf_amd64_979f2262063c03d1\arturiausbmidi.sys` |
  | `midisrv` | 16 | 3 | `C:\WINDOWS\system32\midisrv.exe` |

- **Look 1b:** the user-mode pieces.
  ```
  Get-Item C:\Windows\System32\winmm.dll, C:\Windows\System32\wdmaud2.drv, C:\Windows\System32\midisrv.exe | ForEach-Object { '{0,-12} {1,-22} {2}' -f $_.Name, $_.VersionInfo.FileVersion, $_.VersionInfo.FileDescription }
  ```
- **Printed today** [S:local]:
  ```
  winmm.dll    10.0.26100.1        MCI API DLL
  wdmaud2.drv  10.0.26100.7705     Windows MIDI Services WinMM service interface driver
  midisrv.exe  10.0.26100.7705     Windows Midi Service
  ```
- **Look 1c:** which helpers are loaded.
  ```
  driverquery /v /fo csv | ConvertFrom-Csv | Where-Object { $_.'Module Name' -match 'arturia|ksthunk|USBXHCI|USBHUB3|Ucx|Wdf01000' } | Select-Object 'Module Name',State
  ```
  The machine walk saw `Ucx01000` Running [S:local].
- **What it means:**
  - Type 1 is a kernel driver, loaded into the kernel. Type 16 is a service running in its own process.
  - Start 3 means "on demand": loaded when something needs it.
  - The driver runs straight from the DriverStore, the shelf of installed packages (chapter 5) [S: L16].
  - The "driver" in `wdmaud2.drv` is a DLL that runs inside FL's own process.

**The answer.**
- **Five named kernel layers:** ksthunk, arturiausbmidiks, arturiausbmidi, USBHUB3 and USBXHCI.
- **ACPI** appears on several nodes but stays out of the data path [I].
- **Hidden helpers** never show up as layers: `usbd.sys` and `ks.sys` on Thesycon's side, and on Microsoft's side the USB controller extension `Ucx01000` and the KMDF runtime `Wdf01000` [S:local; I].
- **Above all of these, in user mode:** winmm.dll, wdmaud2.drv and midisrv.exe [S:local; S: G2].

**Teach-back.** Why can a GPU driver update make a game faster, while no KeyLab driver update can make a pad press arrive sooner than USB allows?

**For the lab.** The three positions are three different translators for the same silicon. In positions 1 and 2, FL still sees "a MIDI port". In position 3, our program rebuilds that contract itself.

---

## Chapter 2: User mode and kernel mode (rings, and why a kernel bug is a blue screen)

**The idea.**
- Apps live in fenced yards (ring 3), each with its own private memory. When an app crashes, Windows sweeps up that one yard.
- The kernel and every driver share one big room (ring 0), with full access to memory and hardware and no walls between drivers.
- So when kernel code breaks, Windows cannot know what was damaged. It stops the whole machine on purpose. That stop is a *bugcheck*: the blue screen.

**The analogy.** A machine-check exception. When the CPU finds an ECC error it cannot correct, it halts and logs to WHEA rather than compute on poisoned data. A bugcheck is the operating system's machine check: stopping is cheaper than silent corruption.

There is a middle path, and you have lived it. The GPU driver model (WDDM) splits the display driver in two [S: L17]:
- a user-mode half that compiles shaders and builds command buffers (if it crashes, only the game dies);
- a kernel-mode half that schedules work and manages VRAM.

When the GPU hangs, Timeout Detection and Recovery (TDR) resets the GPU instead of blue-screening the PC [S: L17]. That is a recovery ladder built into Windows. USB-MIDI has nothing like it, which is why the 10-26 hang needed a power cycle [S: G1].

**The deeper level** *(goes deep on IRQL; optional on a first walk, but it is how you read your two blue screens)*:
- On x86-64, the current privilege level sits in the low bits of the code-segment register, and the `syscall` instruction enters ring 0. Windows uses rings 0 and 3. The hypervisor (VBS) sits below the kernel, and AMD's Platform Security Processor sits below that [S: B1; I for the stacking picture].
- Kernel code runs at **interrupt request levels** (IRQLs) [S: L14]:
  - **PASSIVE (0):** ordinary thread work.
  - **DISPATCH (2):** the scheduler and deferred procedure calls (DPCs).
  - **DIRQL:** interrupt handlers.

  At DISPATCH or above, code may not wait and may not touch pageable memory. Breaking that rule is bugcheck 0xD1 or 0xA.

**Predict before you look.** If midisrv crashed tonight, what would happen to FL and the KeyLab? And what if `arturiausbmidi.sys` followed a bad pointer?

**Machine stop 2: your two blue screens, and the service that stayed up.**
- **Look 2a:** the bugcheck reports.
  ```
  Get-WinEvent -FilterHashtable @{LogName='System'; Id=1001; ProviderName='Microsoft-Windows-WER-SystemErrorReporting'} -MaxEvents 5 | Format-List TimeCreated,Message
  ```
- **Printed** [S:local]:
  - `0x9F` with parameter 1 = 3, on 2026-10-21 20:05;
  - `0x133` with parameter 1 = 0, on 2026-08-20 11:13.
- **Look 2b:** `Get-ChildItem C:\Windows\Minidump | Select-Object Name,Length,LastWriteTime`
- **Printed** [S:local]: `082026-25562-01.dmp` (16,777,212 bytes) and `102126-28718-01.dmp` (8,923,884 bytes).
- **Look 2c:** how long midisrv has been up.
  ```
  Get-CimInstance Win32_Process -Filter "Name='midisrv.exe'" | Select-Object ProcessId,CreationDate
  ```
- **Printed** [S:local]: process 45480, started 2026-10-22 03:18:55, using about 13 MB.
- **What it means:**
  - **0x9F/3** means "a device object has been blocking an IRP for too long a time". It was a *power* request, and power requests have a watchdog (chapter 3) [S: L9].
  - **0x133/0** means "a single DPC or ISR exceeded its time allotment": the DPC watchdog (chapter 4) [S: L10].
  - **Which drivers caused them is unknown** until someone reads the dumps. The debugger is already on disk; see the approvals section.
  - **A reading tip [I]:** event 1001 is written *after* the restart. Thesycon's driver also logged a KeyLab arrival at 10-21 20:05, which is most likely the same boot re-detecting the keyboard. So the crash itself happened shortly before 20:05. Nothing here says the KeyLab's driver caused it.
  - **midisrv is a user-mode process** (Type 16) that stayed up through the 10-26 hang and your power cycle. Only the device nodes were rebuilt, at 23:31:45 and 23:31:47 [S:local]. That is the fenced yard working as designed.

**The answer.**
- **If midisrv crashed:** MIDI apps would lose their ports, but the service can start again on demand, and the PC carries on [S:local; I].
- **If the driver followed a bad pointer:** a bugcheck such as 0x50 or 0xD1, and the whole PC goes down [S: bugcheck reference; I].

**Teach-back.** Why does Windows blue-screen instead of just killing the bad driver? Use the machine-check analogy and the "one shared room".

**For the lab.** Positions 1 and 2 run vendor or Microsoft code inside the shared room. Position 3 moves the device logic into a yard of its own: if it crashes, the keyboard goes quiet, but the PC cannot blue-screen because of it.

---

## Chapter 3: How a request travels (IRPs, device stacks, filter, function and bus drivers)

**The idea.** Every I/O operation becomes a packet called an **I/O Request Packet (IRP)**, which is handed down a stack of drivers attached to one device.
- Each layer can handle the request, change it, or pass it down.
- When the bottom layer finishes, the IRP climbs back up, and each layer gets a look on the way.
- The **bus driver** creates the bottom of a stack; it is what says "a device exists here".
- The **function driver** owns the device's behaviour.
- **Filters** slip in above or below the function driver.

**The analogy.** Non-posted PCIe requests. A memory-read TLP travels down through the root port and the chipset switch to the endpoint, and a Completion TLP is routed back up. Every IRP is "non-posted": it must eventually come back completed. A pending IRP is an outstanding tag, and the 10-26 hang looks like an outstanding tag that never got its completion [I].

**The deeper level** *(goes deep, and it matters: this chapter explains both the hang and the toggle)*:
- **How a node is built.** A device node consists of a physical device object (**PDO**, created by the bus driver), optional lower filters, a functional device object (**FDO**, created by the function driver), and optional upper filters [S: L15].
- **How an IRP moves.** The I/O manager gives each IRP one stack location per layer [S: B1].
  - A driver passes it down with `IoCallDriver`.
  - The bottom layer finishes it with `IoCompleteRequest`.
  - Completion routines run on the way back up.
  - `STATUS_PENDING` means "I'll finish later", and Windows allows "later" to mean forever.
- **USB requests.** USB drivers talk to the hub with internal IRPs that carry a **USB Request Block (URB)**. The `usbd.sys` import in Arturia's driver is the helper for building URBs [S:local; S: L15].
- **An LED write, from top to bottom:**
  1. Python calls `midiOutLongMsg`, which goes through wdmaud2.drv to midisrv [S: G2].
  2. midisrv's KS-aggregate transport makes a kernel-streaming write.
  3. The write passes ksthunk, then arturiausbmidiks, then arturiausbmidi.
  4. arturiausbmidi turns it into a URB for a bulk OUT transfer, which goes to USBHUB3, then USBXHCI, then the silicon.
  5. The completion climbs back up.

  [S:local stacks; S: G2; I for the order inside Thesycon's code]
- **Only some requests have watchdogs.**
  - Power IRPs do; that is your 10-21 blue screen [S: L9].
  - Ordinary reads and writes do not. That is why midisrv could wait on the KeyLab "with no time limit" (Pete Brown, microsoft/MIDI #1195) [S: G2].

**Predict before you look.**
1. Will a stuck *write* IRP blue-screen the PC the way the 10-21 power IRP did?
2. Arturia's driver appears in two stacks. What role does it play in each?

**Machine stop 3: five stacks, top to bottom.**
- **Look:** for each instance ID below, run
  ```
  Get-PnpDeviceProperty -InstanceId '<id>' -KeyName DEVPKEY_Device_Stack
  ```
  or, for the KeyLab's subtree:
  ```
  pnputil /enum-devicetree "USB\VID_1C75&PID_02CE\7656400341020110" /stack /drivers
  ```
  The instance IDs:
  - Root port: `PCI\VEN_1022&DEV_14DB&SUBSYS_14531022&REV_00\3&11583659&0&11`
  - xHCI: `PCI\VEN_1022&DEV_43FD&SUBSYS_11421B21&REV_01\6&2766d23f&0&00600011`
  - Root hub: `USB\ROOT_HUB30\7&397afaa3&0&0`
  - KeyLab: `USB\VID_1C75&PID_02CE\7656400341020110`
  - KS child: `TUSBAUDIO_ENUM\VID_1C75&PID_02CE&KS\7656400341020110`
- **Printed today** [S:local]:

  | Node | Stack (top → bottom) | Notes |
  |---|---|---|
  | PCIe root port 1022:14DB | `pci`, `ACPI`, `pci` | The same driver at both ends |
  | xHCI 1022:43FD | `USBXHCI`, `ACPI`, `pci` | |
  | Root hub | `USBHUB3`, `ACPI`, `USBXHCI` | |
  | KeyLab | `arturiausbmidi`, `ACPI`, `USBHUB3` | Its PDO is `\Device\USBPDO-11` |
  | KS child | `ksthunk`, `arturiausbmidiks`, `arturiausbmidi` | ksthunk comes from the MEDIA class's UpperFilters |

- **What it means:**
  - The bottom name created the node (the bus driver's PDO). The top name owns it (the function driver's FDO). Anything in between is a filter.
  - **The root port is the textbook case.** pci.sys created the node (bottom) and also runs the bridge (top) [I].
  - **Each layer is the bus driver for the next one down the tree.** USBXHCI invents the root hub. USBHUB3 runs the root hub and invents the KeyLab's node.
  - **ACPI is on the KeyLab's node** because the BIOS describes port 8 as an ACPI object (`POT8`). It supplies location and power data and stays out of the MIDI path [I].

**The answers.**
1. **No.** Pending forever is legal for ordinary I/O. That is why the hang was silent, and why our own tools need a watchdog [S: L9, G2; I].
2. Arturia's driver is the **function driver** on the USB node and the **bus driver** at the bottom of the KS child's stack [S:local].

**Teach-back.** Draw the KeyLab node's stack from memory. Say which driver created the bottom object (the PDO) and which owns the function object (the FDO).

**For the lab.** The toggle swaps **only the top of the KeyLab node's stack**: arturiausbmidi → usbccgp (position 2) → WinUsb (position 3). `ACPI | USBHUB3` underneath never moves. In position 2, usbccgp becomes a bus driver itself and invents `MI_xx` children, exactly as Thesycon invents `TUSBAUDIO_ENUM…&KS`.

---

## Chapter 4: Interrupts, DMA and polling

**The idea.** Hardware and CPU coordinate in three ways:
- **polling:** keep asking "anything yet?";
- **interrupts:** the device taps the CPU on the shoulder;
- **DMA (direct memory access):** the device moves data to and from RAM by itself and says when it is done.

Then the twist that surprises everyone: **a USB device can never interrupt anything.** The host controller polls the device, DMAs the data into RAM, and then interrupts the CPU itself.

**The analogy.** GPU command queues. The driver writes commands into a ring buffer in RAM and rings a doorbell. The command processor fetches them by DMA, and completion comes back as a fence or an interrupt. The xHCI USB controller works the same way [S: X1]:
- a **transfer ring** of Transfer Request Blocks (TRBs) for each endpoint;
- a **doorbell** register for each device;
- an **event ring** for completions;
- **MSI-X** interrupts. A message-signalled interrupt is simply a memory write over PCIe [S: L18].

NVMe has the same shape, with submission and completion queues.

**The deeper level** *(goes deep; optional on a first walk, but it returns when you read the 08-20 dump and when position 3 posts its own reads)*:
- **ISR and DPC.** The interrupt service routine (ISR) runs at device IRQL, does the minimum, and queues a DPC. The DPC runs at DISPATCH level and completes the IRPs [S: L14]. One DPC or ISR running too long is bugcheck 0x133/0, your 08-20 blue screen [S: L10].
- **Frames.** Full speed runs 1 ms frames; high speed runs 125 µs microframes [S: U1].
- **NAK.** A device answers an IN poll with data or NAK ("nothing yet"), and an OUT with ACK or NAK ("I'm busy"). NAK is flow control, not an error. A transfer the device keeps NAKing stays pending until software cancels it [S: U1; I for the phrasing].
  - A KeyLab that "stops draining its input" (microsoft/MIDI #1084) would look exactly like an endless NAK on its bulk OUT endpoint [S: G2; I].
- **Reads must stay posted.** Pad presses leave the keyboard only while the host has an IN read waiting. Drivers keep reads posted all the time; KMDF calls this a "continuous reader" [S: L12, L13].
- **The IOMMU.** The xHCI's DMA can be fenced by the IOMMU (AMD-Vi) [S: Kernel DMA Protection docs; I].

**Predict before you look.**
1. When you hit a pad, does the KeyLab interrupt your CPU?
2. Was the 08-20 DPC blue screen the KeyLab's driver?

**Machine stop 4: the controller's register window and interrupt lines.**
- **Look:**
  ```
  pnputil /enum-devices /instanceid "PCI\VEN_1022&DEV_43FD&SUBSYS_11421B21&REV_01\6&2766d23f&0&00600011" /resources
  Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Enum\PCI\VEN_1022&DEV_43FD&SUBSYS_11421B21&REV_01\6&2766d23f&0&00600011\Device Parameters\Interrupt Management\MessageSignaledInterruptProperties' | Select-Object MSISupported
  ```
  In Device Manager: Universal Serial Bus controllers → "AMD USB 3.20 eXtensible Host Controller - 1.10 (Microsoft)" → Resources tab.
- **Printed today** [S:local]:
  - **8 interrupt resources**, numbered IRQ -126 to -133;
  - **one memory window**, 0xDD100000 to 0xDD107FFF (32 KB);
  - `MSISupported = 1`.
- **What it means:**
  - The 32 KB window is the controller's register file: where the driver rings doorbells and finds the event-ring pointers [S: X1; I for the mapping].
  - Negative IRQ numbers are message-signalled interrupts. With 8 vectors, completions can land on several cores [I].
  - This is "the controller interrupts the CPU, never the keyboard", made concrete.

**The answers.**
1. **No.** The KeyLab waits for the xHCI's IN poll. The controller writes the bytes to RAM and fires an MSI-X. That interrupt belongs to the controller, never to the keyboard [S: U1, X1].
2. **Unknowable without the dump.** The debugger is on disk; reading the dump needs symbol files (see the approvals section).

**Teach-back.** Explain the transfer ring, the doorbell and the event ring using only GPU words.

**For the lab.** In positions 1 and 2, a write the KeyLab keeps NAKing just waits, with no error anywhere. In position 3, our program sets a per-transfer timeout (`PIPE_TRANSFER_TIMEOUT`), so the same stall becomes a measured, dated fact.

---

## Chapter 5: Plug and Play, and how Windows picks a driver

*Goes deep, and this is the chapter that matters most for the toggle. Take two walks over it if it needs them.*

**The idea.** When a device arrives:
1. Its bus driver reports a list of IDs, from most specific to most generic.
2. Windows searches the driver store for INF files whose model lines name any of those IDs.
3. It scores every candidate and installs the one with the **lowest** score.

Packages you add are copied into the store and renamed `oemNN.inf`.

**The analogy.** Code that picks a path by CPUID. A library carries an AVX-512 path, an AVX2 path and an SSE2 baseline, and runs the most specific one the chip supports.
- **Hardware IDs** are the exact family, model and stepping. `REV_1500` is the device's bcdDevice field, which matches firmware 1.5.0 [S: L11; I for the firmware mapping].
- **Compatible IDs** are feature flags, such as "speaks USB Audio, MIDI Streaming subclass".
- **The driver store** is the shelf of code paths, and the rank is the dispatcher's choice.

**The deeper level.**
- **The rank format.** A rank is `0xSSGGTHHH`: signature score (SS), feature score (GG), then identifier score (THHH). Lower wins [S: L1, L2, fetched].
- **The four match types (T)** [S: L1, fetched]:

  | T | What matched what |
  |---|---|
  | 0 | Device hardware ID → INF hardware ID |
  | 1 | Device hardware ID → INF compatible ID |
  | 2 | Device compatible ID → INF hardware ID |
  | 3 | Device compatible ID → INF compatible ID |

- **HHH** encodes where the matching ID sat in the device's list. When an INF compatible ID matched, it also counts 0x100 for each position along the INF's compatible list.
- **Tie-breaks** are "the most recent date", then "the highest version" [S: selection overview, fetched].
- **A trusted signature** of any kind, "even… MakeCert", earns the best signature score. "AllSignersEqual" has been on by default since Windows 7 [S: L2; selection overview, fetched].
- **Files run straight from the store.** The INF's `ServiceBinary = %13%\arturiausbmidi.sys` becomes an ImagePath inside `…\DriverStore\FileRepository\arturiausbmidi.inf_amd64_979f2262063c03d1\` [S:local; S: L16].

**Predict before you look.** Suppose the parent moves to "USB Composite Device". Microsoft ships two INFs that could take the KeyLab's MIDI part: `usbmidi2.inf` (the new USBMidi2-ACX) and `wdma_usb.inf` (the older usbaudio.sys). **Which wins by default, and why?** Write down your pick before reading on. This is the prediction the course itself got wrong once, and the lab settles it.

**Machine stop 5: the scoreboard.**
- **Look 5a:** the toggle's positions, straight off Windows.
  ```
  pnputil /enum-devices /instanceid "USB\VID_1C75&PID_02CE\7656400341020110" /drivers
  ```
- **Printed today** [S:local]:
  - **oem22.inf:** Arturia 1.7.0.0, rank `00FF0001`, "Best Ranked / Installed", matched on `USB\VID_1C75&PID_02CE`.
  - **usb.inf:** "USB Composite Device" (usbccgp), rank `00FF2006`, "Outranked".
- **Look 5b:** the IDs the KeyLab reported.
  ```
  Get-PnpDeviceProperty -InstanceId 'USB\VID_1C75&PID_02CE\7656400341020110' -KeyName DEVPKEY_Device_HardwareIds,DEVPKEY_Device_CompatibleIds | Format-List KeyName,Data
  ```
- **Printed today** [S:local]:

  | List | # | ID |
  |---|---|---|
  | Hardware IDs | 0 | `USB\VID_1C75&PID_02CE&REV_1500` |
  | | 1 | `USB\VID_1C75&PID_02CE` |
  | Compatible IDs | 0 | `USB\COMPAT_VID_1C75&DevClass_00&SubClass_00&Prot00` |
  | | 1 | `USB\COMPAT_VID_1C75&DevClass_00&SubClass_00` |
  | | 2 | `USB\COMPAT_VID_1C75&DevClass_00` |
  | | 3 | `USB\DevClass_00&SubClass_00&Prot_00` |
  | | 4 | `USB\DevClass_00&SubClass_00` |
  | | 5 | `USB\DevClass_00` |
  | | 6 | `USB\COMPOSITE` |

- **Look 5c:** what the class drivers claim.
  ```
  Select-String -Path C:\Windows\System32\DriverStore\FileRepository\usbmidi2.inf_*\usbmidi2.inf,C:\Windows\System32\DriverStore\FileRepository\wdma_usb.inf_*\wdma_usb.inf -Pattern 'USB\\CLASS_01'
  ```
- **Printed today** [S:local]:
  - `usbmidi2.inf` names `USB\CLASS_01&SUBCLASS_03&PROT_00` as its hardware ID, then the compatible IDs `USB\CLASS_01&SUBCLASS_03` and `USB\CLASS_01`.
  - `wdma_usb.inf` names `USB\CLASS_01` as its hardware ID, and excludes the Audio 2.0 IDs (`…Prot_20`).
- **Look 5d:** precedent on this PC.
  ```
  Get-PnpDevice | Where-Object { $_.Service -in 'usbaudio','USBMidi2','usbccgp' } | Select-Object FriendlyName,Service,Present,InstanceId
  ```
- **Printed today** [S:local]:
  - A class-compliant "USB Midi " device (VID 552D, PID 4348) was plugged in on 2025-12-31 and 2026-01-01. It got usbccgp on the parent and a single `MI_00` child, bound to **usbaudio** through `USB\Class_01` at rank `00FF2005`.
  - The NZXT USB MIC and the C922 webcam's audio function bind the same way today.
  - `USBMidi2` has **no service key**: it has never been bound to anything on this PC.
- **Look 5e:** the scoreboard across the whole machine [S:local values; S: L1, L2 rules, fetched]:

  | Node | Rank | What matched | T |
  |---|---|---|---|
  | KeyLab (Arturia) | 00FF0001 | Hardware ID #1 → INF hardware ID | 0 |
  | MIDI endpoint | 00FF0000 | Hardware ID #0 → INF hardware ID | 0 |
  | Root hub | 00800002 | Hardware ID #2; feature score 80 from the INF | 0 |
  | KeyLab (usb.inf candidate) | 00FF2006 | Compatible ID #6 `USB\COMPOSITE` → INF hardware ID | 2 |
  | xHCI | 00802006 | Compatible ID #6 `PCI\CC_0C0330`; feature score 80 | 2 |
  | PCI bridges | 00FF2007 | Compatible ID #7 | 2 |
  | Past "USB Midi" child | 00FF2005 | Compatible ID #5 `USB\Class_01` | 2 |
  | WinMM port nodes | 00FF3000 | Compatible ID #0 → INF *compatible* ID (c_swdevice.inf leaves its hardware-ID slot empty: `SoftwareDevice,,SWD\GenericRaw`) | 3 |

- **What it means:**
  - **Decoding the KeyLab's rank, `00FF0001`:**

    | Part | Value | Meaning |
    |---|---|---|
    | SS | 00 | Trusted signature |
    | GG | FF | No feature score |
    | T | 0 | Hardware ID matched hardware ID: the best match type |
    | HHH | 001 | The second hardware ID in the list, `USB\VID_1C75&PID_02CE` |

  - **Decoding Windows' composite driver, `00FF2006`:** a compatible-ID match (T = 2) at position 6, `USB\COMPOSITE`.
  - **Rank comes before date.** A class driver can match only through compatible IDs, which score 0x2000 or worse. So while Arturia's package is in the store, Arturia wins automatically, however new Microsoft's driver is [I from L1].
  - **This scoreboard has been printed in plain text before.** On 2026-06-11, Arturia's installer logged "Installing best driver (oem22.inf)", with oem22 at `00FF0001` "Selected" and usb.inf at `00FF2006` "Outranked". The lines are in `C:\Windows\INF\setupapi.dev.20260715_043401.log`, lines 7442 to 7711 [S:local].

**The answer, honestly: two arguments, and the walk's is stronger.**
- **The curriculum's argument (USBMidi2):** USBMidi2 names the MIDIStreaming ID first, and that ID is the most specific one.
- **The machine walk's argument (usbaudio):**
  - Without an Interface Association Descriptor, Windows groups a device's consecutive audio-class interfaces into one child. That child's compatible IDs "are taken… from the first USB interface descriptor in each interface collection" [S: Learn, "Support for interface collections", fetched].
  - For a standard USB-MIDI 1.0 device that first interface is AudioControl (subclass 01), not MIDIStreaming (03) [S: U2; I for the KeyLab].
  - This Windows build also puts three vendor-qualified `COMPAT_VID` IDs first, so the generic `USB\Class_01` lands at position 5.
  - Scoring that position:
    - **wdma_usb** matches it through its hardware-ID slot: `00FF2005`.
    - **usbmidi2** reaches it only through its second INF compatible ID: 0x3000 + 0x100 + 5 = `00FF3105`.

    **usbaudio wins** [S: L1, fetched; I for the KeyLab].
  - The local precedent agrees, and so does Microsoft: "most MIDI 1.0 devices remain on existing drivers by default" [S: overview, via the driver study].
  - **The exception:** if the KeyLab's MIDIStreaming interface is enumerated on its own, usbmidi2 matches at position 3 (`00FF2003`) and wins [I].
- **My read:** probably usbaudio [I]. But the KeyLab's descriptors are unread, so this is still a prediction. The lab's question P1 reads the answer off Windows' own scoreboard.

**Teach-back.** Why will Windows keep choosing Arturia's driver even when Microsoft's is newer? *(Rank comes before date. A hardware-ID match beats any compatible-ID match, and the date only breaks ties.)*

**For the lab.**
- **"Go home" needs no choice and no download.** Asking Windows to install "the best match" lets the scoreboard pick, and the scoreboard picks Arturia.
- **The rank guardrail:** before any switch, check that Arturia is still "Best Ranked". Otherwise home is not safe.

---

## Chapter 6: Driver packages and signing (INF, CAT, Authenticode, attestation, test signing, Secure Boot)

*Goes deep, and it matters. This chapter is why position 3a costs nothing in trust and 3b is your call.*

**The idea.** A driver package has three parts:
- the **INF**, which is the install recipe;
- the **CAT** (catalog), a signed list of hashes for every file in the package;
- the **binaries**.

Windows checks the catalog before it stages a package, and checks kernel code again before loading it. On modern Windows with Secure Boot on, Microsoft itself must sign every kernel driver.

**The analogy.** Engineering samples versus retail chips.
- **WHQL** is full qualification in Microsoft's HLK test lab.
- **Attestation** is the vendor proving its identity with an EV certificate, after which Microsoft scans and countersigns without the full lab. Compare a vendor-declared EXPO profile with a QVL-tested memory kit.
- **Test signing** is ES mode. Any certificate works, a "Test Mode" watermark plays the part of the ES marking, and it only runs where the board allows it.
- **Secure Boot** is the chain of trust: the PSP checks the firmware, the firmware checks the boot manager, and Windows checks every driver.

**The deeper level.**
- **Who signed what.** Arturia's packages are signed by "Microsoft Windows Hardware Compatibility Publisher" with the attributes "Universal, Attested". The binaries carry no embedded signature; they are verified through the catalog. Microsoft's own drivers are signed "Microsoft Windows" [S:local].
- **The kernel-mode policy** [S: L6, fetched]:
  - Since Windows 10 version 1607, Windows "will not load any new kernel-mode drivers which are not signed by the Dev Portal".
  - A Dev Portal account requires an EV code-signing certificate.
  - Attestation covers Windows 10 and later client systems without HLK testing.
  - One exception allows cross-signed drivers: "Secure Boot is off in the BIOS".
- **Test mode** [S: L7, fetched]:
  - The command is `Bcdedit -set TESTSIGNING ON`. With Secure Boot on, it fails with "protected by Secure Boot policy".
  - Test mode shows a "Test Mode" watermark and accepts any certificate.
  - With memory integrity on, binaries must still be test-signed.
- **Two separate checks:**
  - **Staging (Plug and Play):** the package's catalog must be signed, by WHQL or by a test certificate the machine trusts [S: L8, fetched].
  - **Kernel load (code integrity):** every kernel binary must carry Microsoft's signature.

  A WinUSB package passes the second check for free, because its only kernel binary is Microsoft's `winusb.sys`. That is how Zadig/libwdi installs WinUSB with a self-made certificate [S: Z1, L8].

**Predict before you look.**
1. Arturia's driver says "Arturia" everywhere. Whose signature is on it?
2. What would it take to load a kernel driver of our own on this PC tomorrow?

**Machine stop 6: who vouches for each driver.**
- **Look 6a:** the package.
  ```
  pnputil /enum-drivers /class "{463bf520-cdd6-42c5-8602-d96558779b60}"
  ```
- **Printed** [S:local]: `arturiausbmidi.inf` published as oem22.inf, provider Arturia, version 1.7.0.0, signer "Microsoft Windows Hardware Compatibility Publisher", attributes "Universal, Attested".
- **Look 6b:** the binary and its catalog.
  ```
  Get-ChildItem 'C:\Windows\System32\DriverStore\FileRepository\arturiausbmidi.inf_amd64_*\arturiausbmidi.sys' | ForEach-Object { Get-AuthenticodeSignature $_.FullName } | Format-List Status,SignatureType
  Get-ChildItem 'C:\Windows\System32\DriverStore\FileRepository\arturiausbmidi.inf_amd64_*\*.cat' | Select-Object Name,Length
  ```
- **Printed today** [S:local]: Status `Valid`, SignatureType `Catalog`, signer "Microsoft Windows Hardware Compatibility Publisher". The file `arturiausbmidi.cat` is 15,316 bytes.
- **Look 6c:** the machine's signing posture.
  ```
  (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\SecureBoot\State').UEFISecureBootEnabled
  Get-CimInstance -Namespace root\Microsoft\Windows\DeviceGuard -ClassName Win32_DeviceGuard | Format-List VirtualizationBasedSecurityStatus,SecurityServicesRunning,CodeIntegrityPolicyEnforcementStatus
  (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\CI\Config').VulnerableDriverBlocklistEnable
  ```
- **Printed today** [S:local]:
  - Secure Boot `1` (on);
  - VirtualizationBasedSecurityStatus `2`, SecurityServicesRunning `0`, CodeIntegrityPolicyEnforcementStatus `2`;
  - VulnerableDriverBlocklistEnable `1`;
  - no TESTSIGNING in the boot options.
- **What it means:**
  - Arturia's 434 KB driver has no signature of its own. A 15 KB catalog holds its hash, and Microsoft signed the catalog.
  - The hypervisor is up, but memory integrity is not running [I: the Win32_DeviceGuard value meanings].
  - The vulnerable-driver blocklist is on.

**The answers.**
1. **Microsoft's,** through attestation [S:local].
2. **Either Secure Boot off plus test mode,** which weakens the machine and is your call, **or an EV certificate plus a Partner Center attestation submission for every build** [S: L6, L7; I]. That is why the course's custom driver lives in user mode.

**Teach-back.** Explain how a 15 KB catalog lets Windows trust a 434 KB driver that carries no signature of its own.

**For the lab.**
- **Option 3a** (Microsoft's own "WinUsb Device", picked by hand) uses only Microsoft-signed files, so nothing about trust changes.
- **Option 3b** (our own INF) needs a catalog signed by a certificate the machine trusts. Installing that trust is a security change and your call.

---

## Chapter 7: WDM, KMDF and UMDF (how drivers are built)

**The idea.** A driver written from scratch must handle dozens of Plug and Play and power events correctly. That raw model is called **WDM**. Microsoft's frameworks (**WDF**) supply a runtime that runs those state machines for you, so you write only the device-specific parts.
- **KMDF** runs in the kernel.
- **UMDF** runs your driver in a separate user-mode host process. If it crashes, that process dies and the PC stays up.

**The analogy.**
- WDM versus KMDF is hand-written assembly versus a compiler plus runtime.
- UMDF is Zen 2's chiplet move. Putting I/O and memory on a separate IO die cost a hop of latency but bought modularity and fault isolation. UMDF does the same for a driver: one hop slower per request, and a defect takes out one chiplet instead of the whole package.

**The deeper level.**
- KMDF provides framework objects such as `WDFDEVICE`, `WDFQUEUE`, `WDFREQUEST` and `WDFUSBPIPE`. Drivers load it through `wdfldr.sys`, and the INF declares a `KmdfLibraryVersion` [S: L13].
- UMDF 2 uses the same object model but runs in `WUDFHost.exe`, reaching the kernel through a reflector driver, `WUDFRd.sys` [S: L13, B1].
- Microsoft's guidance: use UMDF when it can do the job, and KMDF when you need kernel-only abilities such as serving kernel-mode clients [S: L13].
- **ACX** is Microsoft's newer audio framework, built on KMDF [S: Learn ACX overview].

**Predict before you look.** Three drivers could carry USB-MIDI on this PC: Arturia's, usbaudio and USBMidi2. Which of them use a framework? And what about Microsoft's two layers under the KeyLab?

**Machine stop 7: search the driver files for the framework loader.** A KMDF driver imports from `WDFLDR.SYS`, so that name sits inside the file as plain text.
- **Look:**
  ```
  $files = @('C:\Windows\System32\drivers\USBXHCI.SYS','C:\Windows\System32\drivers\UsbHub3.sys','C:\Windows\System32\drivers\usbaudio.sys','C:\Windows\System32\drivers\WinUsb.sys') + (Get-ChildItem 'C:\Windows\System32\DriverStore\FileRepository\arturiausbmidi.inf_amd64_*\arturiausbmidi.sys','C:\Windows\System32\DriverStore\FileRepository\usbmidi2.inf_amd64_*\USBMidi2.sys' | ForEach-Object FullName)
  foreach($f in $files){ '{0,-20} framework (WDFLDR): {1}' -f (Split-Path $f -Leaf), [bool](Select-String -Path $f -Pattern 'WDFLDR.SYS' -SimpleMatch -Quiet) }
  ```
- **Printed today** [S:local]:
  ```
  USBXHCI.SYS          framework (WDFLDR): True
  UsbHub3.sys          framework (WDFLDR): True
  usbaudio.sys         framework (WDFLDR): False
  WinUsb.sys           framework (WDFLDR): True
  arturiausbmidi.sys   framework (WDFLDR): False
  USBMidi2.sys         framework (WDFLDR): True
  ```
- **The fuller import tally from the machine walk** [S:local]:

  | Driver | Imports | Model |
  |---|---|---|
  | arturiausbmidi | ntoskrnl, HAL, USBD | WDM |
  | arturiausbmidiks | ntoskrnl, HAL, ks | WDM / AVStream |
  | ksthunk | ntoskrnl, ks | WDM filter |
  | usbccgp | ntoskrnl, WMILIB, USBD, WppRecorder | WDM |
  | usbaudio | ntoskrnl, HAL, USBD, ks, WMILIB, WppRecorder | WDM + kernel streaming |
  | USBMidi2 | ntoskrnl, USBD, WDFLDR (INF: `KmdfLibraryVersion = 1.31`, "ACX v1.0 MIDI 2 Driver") | KMDF + ACX |
  | WinUsb | ntoskrnl, HAL, USBD, WppRecorder, WDFLDR | KMDF |
  | UsbHub3 | ntoskrnl, WppRecorder, ksecdd, USBD, WDFLDR | KMDF |
  | USBXHCI | ntoskrnl, HAL, WppRecorder, WDFLDR | KMDF + the UCX extension |

- **What it means:** the KeyLab's path today is **framework-built at the bottom (Microsoft) and hand-built at the top (Thesycon)** [S:local]. Thesycon itself describes TUSBAudio as a "standard WDM/DirectX compatible sound device" [S: T1, fetched].

**The answer.** Of the three MIDI drivers, only USBMidi2 uses a framework. Microsoft's controller and hub layers under the KeyLab are KMDF too, and so is WinUsb.

**Teach-back.** MIDI is tiny data. Why might Microsoft still build its newest MIDI driver on KMDF rather than UMDF? *(It plugs into the kernel's audio and kernel-streaming plumbing, which kernel clients use [I].)*

**For the lab.**
- **Position 1:** hand-built WDM on top of framework layers.
- **Position 2-new:** KMDF + ACX.
- **Position 3:** Microsoft's KMDF WinUsb, with our own logic running safely in user mode.

---

## Chapter 8: USB from the wire up

*Goes deep, but optional on a first walk. The lab's position-2 step reads this chapter's answer off the machine for you.*

**The idea.** USB is a bus the host runs. When you plug something in:
1. the hub notices and resets the port;
2. the host gives the device an address;
3. the host asks the device to describe itself, through its *descriptors*;
4. the host picks a configuration.

A device contains configurations; a configuration contains interfaces (the functions); an interface contains endpoints (one-way mailboxes). There are four transfer types:
- **control:** endpoint 0, for setup and commands;
- **bulk:** reliable, sent whenever there is room;
- **interrupt:** small, polled on a schedule;
- **isochronous:** reserved time and no retries, used for audio and video.

Class specifications (HID, Audio, MIDI) let one Microsoft driver serve every device that follows them.

**The analogy.** PCIe enumeration at boot, done hot.
- At boot, the BIOS walks the bus and reads each function's config space: vendor, device, class code. The USB host reads descriptors instead.
- Assigning BARs corresponds to SET_ADDRESS.
- The class codes are cousins. The xHCI's own compatible ID is `PCI\CC_0C0330` (serial bus, USB, xHCI) [S:local], just as a MIDI interface carries class 01, subclass 03.
- **A composite USB device is a multi-function PCIe device.** Your RX 9070 XT is a GPU function plus an HD Audio function under one PCIe parent, behind its own PCIe switch (AMD 1002:1478/1479) [S:local; I for the function numbering].
- USB 2.0 is a shared front-side bus with the host as the only arbiter. USB 3 SuperSpeed is point-to-point like PCIe, and every USB 3 port also carries a separate USB 2 pair [S: U1].

**The deeper level.**
- **Descriptors** [S: U1, ch. 9]:
  - The device descriptor holds idVendor, idProduct, bcdDevice, bDeviceClass and bNumConfigurations.
  - The configuration descriptor contains interface descriptors (bInterfaceClass, SubClass, Protocol).
  - Endpoint descriptors give the address and direction, the transfer type, wMaxPacketSize and bInterval.
- **Windows builds its IDs straight from these fields** [S: L11; S:local]:
  - `USB\VID_1C75&PID_02CE&REV_1500` is idVendor, idProduct and bcdDevice.
  - `DevClass_00` means "the class is set per interface".
  - `USB\COMPOSITE` means two or more interfaces in one configuration. Without Arturia's package, Windows would load usbccgp and split the device into `…&MI_00`, `…&MI_01` children [S: L4, L5, fetched].
- **Speeds** are 1.5, 12 and 480 Mb/s [S: U1]. The KeyLab's speed is unread.

**Predict before you look.** Judging only from the IDs, what interfaces does the KeyLab have?

**Machine stop 8: what the KeyLab told Windows when it arrived.**
- **Look 8a:**
  ```
  Get-PnpDeviceProperty -InstanceId 'USB\VID_1C75&PID_02CE\7656400341020110' -KeyName DEVPKEY_Device_HardwareIds,DEVPKEY_Device_CompatibleIds,DEVPKEY_Device_Capabilities,DEVPKEY_Device_LocationInfo | Format-List KeyName,Data
  ```
- **Printed today** [S:local]:
  - The two hardware IDs and seven compatible IDs listed in chapter 5, ending in `USB\COMPOSITE`.
  - Capabilities `148`.
  - Location `Port_#0008.Hub_#0002`.
- **Look 8b:** did it offer Windows a Microsoft OS descriptor?
  ```
  Get-ChildItem HKLM:\SYSTEM\CurrentControlSet\Control\usbflags | Where-Object PSChildName -like '1C7502CE*' | ForEach-Object { '{0}  osvc={1}' -f $_.PSChildName, (($_.GetValue('osvc')) -join ' ') }
  ```
- **Printed today** [S:local]:
  ```
  1C7502CE0500  osvc=0 0
  1C7502CE1101  osvc=0 0
  1C7502CE1201  osvc=0 0
  1C7502CE1500  osvc=0 0
  ```
- **What it means:**
  - **Capabilities 148** is 0x94: Removable (0x04) + UniqueID (0x10) + SurpriseRemovalOK (0x80), decoded with the local SDK's cfgmgr32.h [S:local].
    - "UniqueID" means the instance ID is the keyboard's serial number, `7656400341020110`. A driver choice therefore follows the keyboard to any port [S:local; S: M1].
  - **Four revisions have been seen:** 0500, 1101, 1201 and 1500 [S:local]. The last-write times of those keys date the firmware updates (lab section L2).
  - **`osvc = 0 0`** means Windows asked for Microsoft's OS descriptor and got none. **So WinUSB can never bind to the KeyLab automatically** [S:local; I].
  - **The `COMPAT_VID_1C75…` IDs** are this Windows build's vendor-qualified extras, listed before the generic ones [S:local].

**The answer.**
- At least two interfaces in one configuration. A class-compliant MIDI device pairs AudioControl (01/01) with MIDIStreaming (01/03), and the MIDI spec requires the AudioControl interface [S: U2].
- Possibly a firmware-update interface as well (DFU class FE/01) or a vendor interface (FF) [I].
- The descriptors themselves are unread. Two ways to read them:
  - **USBView, already on this PC.** Running it is a separate go (see the approvals section).
  - **The lab's position-2 step,** which prints each `MI_xx` child's interface class for free.

**Teach-back.** Explain to Simon why a USB keyboard cannot push a keypress, and who decides when it leaves.

**For the lab.** In position 2, usbccgp turns each interface, or interface collection, into an `MI_xx` child. Those children's compatible IDs *are* the KeyLab's interface descriptors, printed by Windows itself.

---

## Chapter 9: USB-MIDI 1.0 (4-byte event packets, cables, SysEx framing)

*Goes deep, and it is the most hands-on chapter.*

**The idea.** On a DIN cable, MIDI is a stream of messages of varying length. USB-MIDI chops that stream into fixed 4-byte packets:
- one header byte that says which virtual cable and what kind of message;
- up to three MIDI bytes.

A SysEx message can be any length. It travels as a chain of packets marked "starts or continues", ending with one marked "ends here with 1, 2 or 3 bytes".

**The analogy.** x86 decoding.
- x86 instructions run from 1 to 15 bytes, so the front end works hard just to find where each one starts. The core turns them into fixed-width micro-ops tagged with pre-decoded lengths.
- MIDI 1.0 bytes are the x86. USB-MIDI packets are the micro-ops. The **Code Index Number (CIN)** is the pre-decode tag.
- The **cable number** is like an SMT thread tag that lets two streams share one pipe.
- MIDI 2.0's packet format (UMP) is fixed-width from the start, 32 to 128 bits: the RISC version [S: U3].
- The burst governor (12 SysEx per 100 ms) fits this picture too. The wire is nowhere near full; the keyboard's small CPU is the bottleneck, the way a game can be CPU-bound on draw calls rather than GPU-bound [I].

**The deeper level.**
- **Byte 0** holds the cable number in the high nibble (0 to 15) and the CIN in the low nibble [S: U2, §4, Table 4-1]:

  | CIN | MIDI bytes | Meaning |
  |---|---|---|
  | 2 | 2 | Two-byte system common |
  | 3 | 3 | Three-byte system common |
  | 4 | 3 | SysEx starts or continues |
  | 5 | 1 | SysEx ends with one byte, or a single-byte system common |
  | 6 | 2 | SysEx ends with two bytes |
  | 7 | 3 | SysEx ends with three bytes |
  | 8 / 9 | 3 | Note off / note on |
  | A | 3 | Polyphonic pressure |
  | B | 3 | Control change |
  | C | 2 | Program change |
  | D | 2 | Channel pressure |
  | E | 3 | Pitch bend |
  | F | 1 | Single byte |

- **MIDI travels on bulk endpoints** [S: U2]. One 64-byte full-speed bulk packet carries up to 16 event packets [S: U1; arithmetic].
- **Your own bytes, encoded:**
  - **Device Inquiry** `F0 7E 7F 06 01 F7` becomes `04 F0 7E 7F` + `07 06 01 F7` on cable 0, or `14 …` + `17 …` on cable 1.
  - **Its 17-byte reply** becomes five CIN-4 packets plus `06 vv F7 00`: 6 packets, 24 bytes on the wire.
  - **A pad press on the DAW port,** `99 00 7F` [S: G1], becomes `19 99 00 7F`. Its pressure sweep `A0 00 49` becomes `1A A0 00 49`.
- **Timing.** On a DIN cable (31,250 baud, 10 bits per byte), a 15-byte LED message takes 4.8 ms [S: MIDI 1.0 spec; arithmetic]. On USB it fits in one 1 ms frame [I].
- **SysEx rules.** Data bytes must stay below 0x80, and our `sysex()` refuses anything else [S:local]. An unterminated SysEx makes Windows swallow the messages after it; a lone `F7` clears it [S: G2].

**Predict before you look.** How many packets does the Device Inquiry take, and what is the second packet's first byte?

**Machine stop 9: pack your own LED message.**
- **Look 9a: what our code builds.** In `E:\AI-Setup\arsenal\keylab\protocol.py`, `set_led` (lines 215-219) wraps a payload in the KeyLab envelope (line 21). Pad 1 in the DAW bank, blue, comes out as [S:local]:

  ```
  F0 00 20 6B 7F 42 00 02 03 52 00 00 7F 00 F7
  ```

  | Bytes | Meaning |
  |---|---|
  | `F0` | SysEx start |
  | `00 20 6B` | Arturia's manufacturer ID |
  | `7F 42` | The device |
  | `00` | Request |
  | `02` | DAW context |
  | `03` | Set LED |
  | `52` | Pad 1 in the DAW bank (82) |
  | `00 00 7F` | Red, green, blue |
  | `00` | Trailing zero |
  | `F7` | SysEx end |

  The module's own self-test checks the green version of this exact frame (line 319).
- **Look 9b: do the packing yourself.** Pure arithmetic; it touches no device.
  ```
  @'
  msg = bytes.fromhex("F0 00 20 6B 7F 42 00 02 03 52 00 00 7F 00 F7")
  cable = 1                      # 0 = the "MIDI" port, 1 = the "DAW" port
  for i in range(0, len(msg), 3):
      chunk = msg[i:i+3]
      last = i + 3 >= len(msg)
      cin = (4 + len(chunk)) if last else 4   # 4 = SysEx continues; 5/6/7 = ends with 1/2/3 bytes
      print(f"{cable << 4 | cin:02X} " + chunk.ljust(3, b"\0").hex(" ").upper())
  '@ | py -B -
  ```
- **Printed today** [S:local, run from the scratchpad]:
  ```
  14 F0 00 20
  14 6B 7F 42
  14 00 02 03
  14 52 00 00
  17 7F 00 F7
  ```
- **Look 9c: the cable numbers on the machine.** The four WinMM port nodes end in `_0_0` ("MIDI", in), `_0_1` ("DAW", in), `_1_0` ("MIDI", out) and `_1_1` ("DAW", out) [S:local]. The first digit is the direction and the second is the port. That supports cable 0 = MIDI and cable 1 = DAW [I, strong].

**The answer.** Two packets. The second packet's first byte is `07` on cable 0, or `17` on cable 1.

**Teach-back.** Hand-encode "pad 1 magenta" (red 7F, green 00, blue 7F).
*(Answer: `14 F0 00 20 / 14 6B 7F 42 / 14 00 02 03 / 14 52 7F 00 / 17 7F 00 F7`. Change the colour line in Look 9b and check yourself.)*

**For the lab.** In positions 1 and 2, the driver does this packing and apps never see packets [I]. In position 3, those seven lines of Python *are* our program's job, together with unpacking in the other direction and reassembling SysEx per cable.

---

## Chapter 10: The Windows MIDI stack (WinMM, kernel streaming, Windows MIDI Services, class drivers, vendor drivers)

**The idea.** Apps no longer talk to MIDI drivers directly. On this PC, every MIDI app goes through the Windows MIDI Services service, midisrv, which:
- owns the single connection to each device and shares it among apps;
- converts between MIDI 1.0 bytes and MIDI 2.0 packets.

Below midisrv sit **kernel-streaming (KS)** drivers: either Microsoft's class drivers for compliant devices, or a vendor's driver such as Arturia's Thesycon build.

**The analogy.** The IO die.
- Zen's core dies never touch DRAM or PCIe directly; everything crosses Infinity Fabric to the IO die, which arbitrates and translates. **midisrv is the KeyLab's IO die.** FL, the screen service and the CLI all share one device through it.
- The price is an extra hop and a single point of failure: when the service wedges, everyone wedges (#1084) [S: G2].
- The **KS-aggregate (KSA)** transport presents all of a device's KS pins as one MIDI 2.0 endpoint [S: M2, fetched].
- **Thesycon is the reference board.** Arturia ships Thesycon's driver with its own name on the box: same die, different shroud.

**The deeper level.**
- **The path down:**
  1. An app calls winmm.dll.
  2. winmm.dll loads `wdmaud2.drv`.
  3. wdmaud2.drv hands the message to midisrv. `midiOutLongMsg` is synchronous, uses 2,048-byte chunks and waits 1,000 ms for "send complete" [S: G2].
  4. midisrv's KSA transport writes to the KS filter on the `TUSBAUDIO_ENUM…&KS` child (arturiausbmidiks).
  5. From there it goes to arturiausbmidi and onto USB.
- **midisrv's other transports:** loopback, app-made virtual devices, Bluetooth LE and network [S: M4, fetched].
- **Microsoft's class drivers here** [S:local]:
  - usbaudio.sys (WDM + KS, for USB Audio 1.0 including MIDI);
  - usbaudio2.sys (Audio 2.0);
  - USBMidi2.sys (KMDF + ACX).
- **Microsoft's warning:** "If a device needs a driver from its manufacturer, neither of these two drivers will work for it" [S: M1, fetched].

**Predict before you look.** When FL and our screen service both hold the DAW port, how many connections does the KeyLab's USB link carry?

**Machine stop 10: from KS pins to the names FL sees.**
- **Look 10a:** the KS child's pins.
  ```
  pnputil /enum-devices /instanceid "TUSBAUDIO_ENUM\VID_1C75&PID_02CE&KS\7656400341020110" /interfaces
  ```
- **Printed** [S:local]:
  - `midi_out_00_00` "MIDI" and `midi_out_01_01` "DAW", registered under KSCATEGORY_AUDIO and **KSCATEGORY_RENDER**;
  - `midi_in_00_00` and `midi_in_01_01`, under KSCATEGORY_AUDIO and **KSCATEGORY_CAPTURE**;
  - the "Topology" interface "USB Audio Mixer", disabled.
- **Look 10b:** the Windows MIDI Services endpoint.
  ```
  pnputil /enum-interfaces /class "{e7cce071-3c03-423f-88d3-f1045d02552b}" /properties
  ```
- **Printed** [S:local]:
  - `SWD\MIDISRV\MIDIU_KSA_16201702556534547415`, driver section `NO_DRV`, stack `\Driver\SoftwareDevice` only;
  - transport "KSA", manufacturer "Arturia", a pin table naming the four pins;
  - group names "KeyLab 88 mk3 MIDI" and "KeyLab 88 mk3 DAW 2".
- **Look 10c:** the transports and the WinMM wiring.
  ```
  Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\Windows MIDI Services\Transport Plugins'
  Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Drivers32' | Select-Object midi,midi1,midimapper,MidisrvTransferComplete
  ```
- **Printed** [S:local]:
  - transports KSA, KS, Loopback and Virtual, all Enabled=1;
  - `midi1=wdmaud2.drv`, `midi=wdmaud.drv` (legacy), `midimapper=midimap.dll`, `MidisrvTransferComplete=1`.
- **Look 10d:** the names FL sees. From `E:\AI-Setup`, run `py -m arsenal.keylab ports`. It asks midisrv for the list and opens no port.
- **Printed** [S:local]:

  | Direction | Index | Name |
  |---|---|---|
  | In | 0 | KeyLab 88 mk3 MIDI |
  | In | 1 | KeyLab 88 mk3 DAW |
  | Out | 0 | Microsoft GS Wavetable Synth |
  | Out | 1 | KeyLab 88 mk3 MIDI |
  | Out | 2 | KeyLab 88 mk3 DAW |

- **What it means:**
  - **"Render"** is PC to keyboard (LED and screen writes). **"Capture"** is keyboard to PC (keys and pads).
  - The endpoint node has no kernel driver at all. midisrv publishes it so apps can find the device.
  - **Every port reports manufacturer 1 (Microsoft)** and a "MS Vanilla driver" product ID. Arturia's identity survives only in the name [S:local]. The names come from the KeyLab's own descriptors, through Thesycon's pins [S: driver study].

**The answer.** One. midisrv holds the device and shares it among the apps above it [S: G2; I].

**Teach-back.** Where would you put probes to tell "midisrv is stuck" apart from "the driver or the device is stuck"? *(Compare the native endpoint monitor with a WinMM monitor, as in step 3 of the hang guide's ladder; below the driver, use a USB trace [S: G2].)*

**For the lab.** The names are the fragile part.
- **In position 2** they may change, for example to "MIDIOUT2 (KeyLab 88 mk3)" [S: naming KB, fetched].
- **Our own code has a trap here.** `_match` in `arsenal/keylab/winmidi.py` (lines 76-89) prefers a name containing "daw" and otherwise falls back to the first "keylab" port. Under Windows' classic names, LED and screen SysEx would silently go to the MIDI cable [S:local; I].
- **In position 3,** our program republishes the original names.

---

## Chapter 11: Userspace drivers (WinUSB, libusb, virtual ports)

**The idea.** You don't need kernel code to drive a USB device. Microsoft ships a generic kernel driver, **WinUSB**, that simply exposes a device's endpoints as pipes to a program. The program then speaks the device's protocol itself; here, the USB-MIDI packets of chapter 9. If other apps such as FL should still see the device, the program publishes virtual MIDI ports. That program is the "userspace driver".

**The analogy.** Mantle, then Vulkan and DX12. DX11 drivers did heavy lifting behind the app's back. Mantle, and after it Vulkan and DX12, made the driver thin and handed command buffers and synchronisation to the app.
- WinUSB is the thin driver, libusb is a portable loader on top of it, and our program is the engine.
- You get the freedom, and you take on the responsibility: pacing, recovery and timeouts become yours. That is exactly the watchdog the hang taught us we need.

**The deeper level.**
- **The WinUSB API.** WinUSB is winusb.sys (Microsoft-signed) plus the winusb.dll API: `WinUsb_ReadPipe`, `WinUsb_WritePipe`, and `WinUsb_SetPipePolicy`, where `PIPE_TRANSFER_TIMEOUT` gives each transfer a deadline [S: L12]. midisrv's KS write lacked exactly that deadline [S: G2; I].
- **Two ways to bind WinUSB to a device** [S: L12]:
  - an INF that names the device or one of its interfaces;
  - Microsoft OS descriptors in the device's own firmware, which the KeyLab lacks (chapter 8).
- **libusb** uses WinUSB underneath on Windows, and Zadig/libwdi generate the INF and a self-signed catalog [S: Z1].
- **One function driver per node.** If WinUSB owns the node, neither Arturia's driver nor a class driver can [S: L4, L5 model; I].
- **How FL keeps a KeyLab** [S: M3, fetched]:
  - Only apps built on the Windows MIDI Services SDK can create a **Virtual Device App** endpoint.
  - WinMM apps like FL can connect to it, MIDI 1.0 only.
  - "When the application closes, the endpoint closes."
- **A second kind of "userspace driver" swaps no driver at all.** Our own long-lived service owns the KeyLab's ports through Windows MIDI Services and republishes them to everyone else. `arsenal/keylab` already lives at that altitude, and the hub plan builds it first [I; S: driver study §2.4].

**Predict before you look.** If WinUSB owned the KeyLab, what would FL's MIDI settings show?

**Machine stop 11: WinUSB is here, and one door is already open.**
- **Look 11a:** what Microsoft's WinUSB INF matches.
  ```
  Select-String -Path C:\Windows\INF\winusb.inf -Pattern 'MS_COMP_WINUSB|Class_11|Class_ff'
  ```
- **Printed** [S:local]: the model "WinUsb Device" matches `USB\MS_COMP_WINUSB`. Its other lines cover `USB\Class_11…` (billboard devices) and `USB\Class_ff&SubClass_42&Prot_01` (Android debugging). The setup class is `USBDevice`.
- **Look 11b:** the KeyLab's device interfaces, its "doors".
  ```
  pnputil /enum-devices /instanceid "USB\VID_1C75&PID_02CE\7656400341020110" /interfaces
  ```
- **Printed** [S:local; the {A5DCBF10} line re-read during assembly]:

  | GUID | Status | What it is |
  |---|---|---|
  | {A5DCBF10…} | Enabled | Windows' generic "a USB device is here" door (usbiodef.h) |
  | {B68E4561…} | Enabled | The `InterfaceGUID` Arturia's INF writes, so TUSBAudio's private control door [I] |
  | {B68E4562…} | Disabled | Role unknown; strings suggest a firmware-update (DFU) door [I] |
  | {FD0505C2…} | Disabled | Role unknown |

- **What it means:**
  - **WinUSB is in the store but has no automatic path to the KeyLab.** None of its IDs match, and the KeyLab offers no OS descriptor (`osvc = 0 0`, chapter 8). Only a manual pick or an INF of ours can bind it [S:local; I].
  - **The generic door {A5DCBF10} is how option 3a could open the device** before our own `DeviceInterfaceGUIDs` value exists [S:local; I that WinUSB accepts it].

**The answer.** No KeyLab hardware ports at all. FL would show only whatever virtual ports our program publishes [I].

**Teach-back.** What does a userspace driver gain, and what must it now do that Thesycon's driver used to do?
- **Gains:** no kernel code, crash safety, timeouts, full visibility.
- **New duties:** packing and unpacking packets, keeping IN reads posted, recovering after an unplug, publishing ports.
- **Losses:** the vendor's firmware-update path.

**For the lab.** This chapter *is* position 3.
- The curriculum assumed WinUSB would sit on one interface under usbccgp.
- The toggle design puts it on the whole device first, a single-node swap against Arturia, and keeps "usbccgp + WinUSB on `MI_00`" as the fallback.

---

## Capstone lab: the toggle

Everything above was looking. This lab is the first time anything changes, and every switching step waits for your go.

### L1. The design on one page

**Five principles.**
1. **Windows holds the truth.** The current position is whatever driver sits on the KeyLab's node (plus its MIDI child in position 2). The tool reads that live every time. Receipts are history, not state.
2. **Arturia is home, and the moves form a star.** Allowed moves are 1↔2 and 1↔3; going from 2 to 3 passes through 1. Every failure returns to 1. This is DualBIOS: one image always boots.
3. **One primitive.** Windows' `DiInstallDevice` acts on a single device instance [S: Learn, fetched].
   - With a named driver, it goes to that position.
   - With no driver named, it installs "the driver that is the best match" from the store, and on this PC that is Arturia's (chapter 5).

   So **"go home" works like Load Optimized Defaults**: Windows' own scoreboard makes the choice.
4. **The rank guardrail.** Before every switch, check that Arturia's `arturiausbmidi.inf` is "Best Ranked" for the KeyLab. If it isn't, refuse: home would not be safe.
5. **No kernel code of ours in any position.**
   - Positions 1 and 2 run attested or in-box drivers.
   - Position 3 runs Microsoft's own `winusb.sys`.
   - So Secure Boot, test mode and memory integrity never come into it (chapter 6).

**Why not the obvious tools** [S: Learn, fetched; S:local]:
- **pnputil** has no verb that puts a chosen driver on a chosen device.
- **`UpdateDriverForPlugAndPlayDevices` with FORCE** updates *every* device matching the ID you give it. Matching on `USB\COMPOSITE` would also hit the webcam, the NZXT mic and the RGB controller.

**The three positions**

| | **1. Arturia (home)** | **2. Microsoft class driver** | **3. WinUSB + our program** |
|---|---|---|---|
| **KeyLab node's stack** | `arturiausbmidi \| ACPI \| USBHUB3` (oem22) [S:local] | `usbccgp \| ACPI \| USBHUB3` (usb.inf "USB Composite Device") | `WinUsb \| ACPI \| USBHUB3` [I] |
| **Children** | The KS child; midisrv's KSA endpoint; 4 WinMM nodes [S:local] | An `…&MI_00` audio function with usbaudio (predicted) or USBMidi2-ACX (picked by hand); possibly a driverless `MI_0x` for an update interface; a new midisrv endpoint [I] | None. Our program publishes a Windows MIDI Services Virtual Device [I] |
| **Device Manager shows** | "Arturia USB MIDI Devices" → KeyLab 88 mk3; Sound, video and game controllers → KeyLab 88 mk3 [S:local] | Universal Serial Bus controllers → USB Composite Device; Sound, video and game controllers → KeyLab 88 mk3 [S: M1; I] | Universal Serial Bus devices → "WinUsb Device" (3a) or "KeyLab 88 mk3 (WinUSB, Aurora)" (3b) [S: Learn; I] |
| **Packages needed** | oem22 + oem11, already in the store | usb.inf + wdma_usb.inf or usbmidi2.inf, in-box | winusb.inf, in-box (3b adds our INF + catalog) |
| **Firmware updates** | Yes: MIDI Control Center uses `TUSBAUDIO_StartDfuDownload` [S:local strings] | No; go home first [I] | No; go home first [I] |
| **Who writes to the USB pipes** | Thesycon's driver | usbaudio or USBMidi2 | Our process, with timeouts and recovery |

**Toggling means re-binding, never uninstalling.** Every package stays in the store. Deleting Arturia's package to "turn it off" would make home unreachable without running a vendor installer.

### L2. What the machine has already taught us about switching

**Arturia's own installer did this exact switch on this PC on 2026-06-11** [S:local, `setupapi.dev.20260715_043401.log`, lines 4505-4591 and 7442-7711]:

| Time | Step |
|---|---|
| 21:31:41 | `DiUninstallDevice` on the KS child. midisrv's endpoint and the four WinMM nodes go first ("Query-and-Remove succeeded"); midisrv let go without fuss |
| 21:31:42 | `DiInstallDevice`: "Installing NULL driver" on the KeyLab |
| 21:31:47 | The old 1.6.0.0 package (oem64.inf) is deleted |
| 21:32:03 | The new packages are staged as oem22 and oem11 |
| 21:32:04 | "Installing best driver (oem22.inf)": oem22 `00FF0001` "Selected", usb.inf `00FF2006` "Outranked" |

- The device restarted within half a second, with no reboot line [S:local].
- **Lesson 1:** a live switch completes on this PC while midisrv is running.
- **Lesson 2:** `oemNN` numbers get recycled, so always find packages by their original name.

**A firmware update does not make Windows pick a driver again** [S:local, last-write times of the `usbflags` keys; I for the readings]:

| Key | Last written | Reading |
|---|---|---|
| `1C7502CE0500` | 2026-01-24 20:28:21 | An "updater" identity: same product ID, revision 0500 [I] |
| `1C7502CE1201` | 2026-01-24 20:35:42 | Firmware 1.2.1, seven minutes later: one update session [I] |
| `1C7502CE1500` | 2026-06-11 21:52:39 | Firmware 1.5.0, twenty minutes after the driver update; no new driver install followed [S:local; I, strong] |

- **The KeyLab once appeared without its serial number.** An instance with a port-based ID, `USB\VID_1C75&PID_02CE\8&D1AFB05&0&4`, existed until Storage Sense removed it on 2026-01-28 [S:local]. The 01-24 updater mode is the likeliest moment [I].
- To Windows that is a brand-new device, bound purely by rank: Arturia's, as long as its package stays best-ranked [I].
- **Consequences for the design:**
  - Never delete Arturia's packages.
  - Never let a package of ours outrank Arturia's.
  - Start firmware updates only from position 1.

**What holds the KeyLab right now** [S:local, process list, 2026-10-27]:
- Arturia Software Center and its tray Agent (the Agent links Thesycon's API);
- `py -m arsenal.keylab vj --no-leds --quiet`;
- midisrv.

All of them except midisrv must close before any switch.

### L3. Position 2 in detail

- **Default: usbaudio ("2-classic"). USBMidi2-ACX ("2-new") is an explicit second pick** (the chapter 5 argument).
- **Why usbaudio is the better first A/B [I]:** it keeps midisrv on the same KS-aggregate transport Arturia's driver uses. Comparing positions 1 and 2 then changes only the kernel driver, not the service path.
- **Why 2-new is still worth a later visit:**
  - It is Microsoft's future direction.
  - Its source is open (MIT), at github.com/microsoft/MIDI `src/in-box/Drivers/USBMIDI2` [S: driver study].
  - It is chapter 7's KMDF + ACX running live.
  - **Caveat:** it puts the device to sleep after 15 idle minutes [S: driver study, `Device.cpp` lines 452-459], which adds a power variable.
- **How Microsoft says to move a device between the two class drivers** [S: M1, fetched]:
  - "close your DAW and any other app that's using MIDI".
  - Device Manager → Update driver → "Browse my computer for drivers" → "Let me pick from a list of available drivers on my computer" → choose "USB Audio Device" or "USBMidi2-ACX".
  - "When it's done, unplug the device, restart your PC, and plug the device back in."
  - "There's a Plug and Play bug in Windows right now that can put the old driver back after an update." For us that is the safe direction.
- **The KeyLab needs one step first,** because Arturia's driver holds the whole device: pick "USB Composite Device" on the parent node. Microsoft's steps then apply to the child [S: driver study; I].

### L4. Position 3 in detail

**Which node gets WinUSB** [I]:
- **Primary: the whole device**, the node Arturia's driver holds today. Moving between 1 and 3 is then a single-node swap. Our program opens interface 0 with `WinUsb_Initialize` and reaches the MIDIStreaming interface with `WinUsb_GetAssociatedInterface` [S: L12; I that this works here].
- **Fallback: usbccgp on the parent and WinUSB on `MI_00` only.** Microsoft recommends this pattern for composite devices [S: Learn, supported USB classes].

**Binding and signing options** (chapter 6 in practice):

| Route | Signed by | Trust change | Switching | Verdict |
|---|---|---|---|---|
| **3a.** Let me pick → Universal Serial Bus devices → "WinUsb Device", then add a `DeviceInterfaceGUIDs` value and reconnect [S: Learn winusb-installation, fetched] | Microsoft (in-box) | None | Manual pick each time | **Recommended first** |
| **3b.** Our own INF + catalog, signed with a throwaway certificate | A self-made certificate in Trusted Root and Trusted Publisher | Yes: a machine-wide root certificate | One command | **Your call,** and only if position 3 becomes a daily position |
| Zadig/libwdi itself | Same as 3b, with its own tooling | Yes | One click, but its INF's rank is not ours to control [I] | Avoid |
| An unsigned INF | — | — | — | Refused: a package must be signed to be staged [S: L8, fetched] |

**What 3b's certificate would mean.** libwdi's own FAQ says the private key "is generated at runtime, on the end user machine" and "is destroyed after driver package signing completes", so "nobody … [has] the ability to reuse these certificates" [S: libwdi FAQ, fetched]. Ours would do the same, and also [I]:
- be limited to code signing;
- have its thumbprint recorded in the receipt;
- have written removal steps: `certutil -delstore Root <thumbprint>` and `certutil -delstore TrustedPublisher <thumbprint>`.

**The 3b INF.** *(Goes deep. This is chapter 5's rank arithmetic used on purpose. It is a design sketch; nothing has been built or installed.)*

```
; keylab_winusb.inf -- position 3b (design sketch)
[Version]
Signature   = "$Windows NT$"
Class       = USBDevice
ClassGUID   = {88BAE032-5A81-49f0-BC3D-A4FF138216D6}
Provider    = %Mfg%
CatalogFile = keylab_winusb.cat
DriverVer   = 01/01/2000,0.0.0.1     ; old on purpose: loses every tie
PnpLockdown = 1

[Manufacturer]
%Mfg% = Aurora,NTamd64

[Aurora.NTamd64]
; hardware-ID slot left EMPTY, the KeyLab's ID in the compatible slot:
; Windows scores this 0x1001, one rung below Arturia's 0x0001, so it is
; never chosen automatically (not on replug, not for the REV 0500 updater
; identity), only by an explicit pick.
%Desc% = KeyLab_WinUsb, , USB\VID_1C75&PID_02CE

[KeyLab_WinUsb]
Include = winusb.inf
Needs   = WINUSB.NT
[KeyLab_WinUsb.Services]
Include = winusb.inf
Needs   = WINUSB.NT.Services
[KeyLab_WinUsb.HW]
AddReg  = KeyLab_AddReg
[KeyLab_AddReg]
HKR,,DeviceInterfaceGUIDs,0x10000,"{<one fixed GUID of ours>}"

[Strings]
Mfg  = "Akashic Aurora (local)"
Desc = "KeyLab 88 mk3 (WinUSB, Aurora)"
```

- **Why the empty first slot works.** A device hardware ID that matches an INF *compatible* ID scores in the 0x1000 range [S: L1, fetched; I for applying it here]. The empty-slot syntax is the same one `c_swdevice.inf` uses on this PC [S:local].
- **The opposite case.** An INF naming `USB\VID_1C75&PID_02CE&REV_1500` as its hardware ID would score 0x0000 and *beat* Arturia, making ours the automatic default. That is exactly what must never happen [S: L1; I].
- **No collision with Arturia.** Arturia's INF writes `InterfaceGUID`, a different value name from WinUSB's `DeviceInterfaceGUIDs` [S:local; S: Learn].
- **One-time setup** [I]. Every tool is already on this PC: makecat, signtool and MakeCert in the Windows SDK, plus PowerShell's `New-SelfSignedCertificate` [S:local].
  1. Build the catalog with makecat.
  2. Create a code-signing certificate.
  3. Sign the catalog with `signtool sign /fd sha256`.
  4. Import the public certificate into Root and TrustedPublisher.
  5. Delete the private key.
  6. Stage the package with `pnputil /add-driver keylab_winusb.inf`, **without `/install`**.
  7. Verify that `pnputil … /drivers` lists ours as "Outranked" at about `00FF1001`. If it says "Best Ranked", delete it at once.

**What our program does in position 3** (the hub from the driver study, with its bottom layer swapped to WinUSB pipes) [I, except where cited]:
- **Opening:** open the device by our interface GUID, or in 3a through the generic {A5DCBF10} door, then call `WinUsb_Initialize`. Find the MIDIStreaming interface (class 01, subclass 03) and its bulk IN and OUT pipes.
- **OUT (to the keyboard):** one transfer in flight, no longer than the packet size, a 1,000 ms `PIPE_TRANSFER_TIMEOUT` [S: L12]. On timeout: abort, then reset the pipe, then probe.
- **IN (from the keyboard):** 2 to 4 reads always posted, with `RAW_IO` and `AUTO_CLEAR_STALL` [S: L12].
- **The codec from chapter 9:** SysEx reassembled per cable.
- **Queues and pacing:**
  - one queue per cable, so the DAW cable cannot block the keys;
  - the governor (12 SysEx per 100 ms; screen frames at least 60 ms apart);
  - a Device Inquiry heartbeat.
- **Recovery ladder:** abort/reset → reopen → port cycle (admin) → a human replug.
- **Power:** WinUSB never puts the device to sleep unless `DeviceIdleEnabled` is set [S: driver study].
- **FL's ports:** a Windows MIDI Services Virtual Device named "KeyLab 88 mk3 MIDI" and "KeyLab 88 mk3 DAW". It exists only in position 3, so the names never collide with Arturia's real ports. This needs the Windows MIDI Services Tools/SDK runtime, which is not installed (approvals section) [S: M3; S: driver study].

### L5. The switch tool (design only; built after the experiment)

The verb would be `py -m arsenal.keylab driver …`: a 64-bit Python ctypes helper over `setupapi.dll`, `newdev.dll` and `cfgmgr32.dll`. From 32-bit Python the calls fail with `ERROR_IN_WOW64` [S: Learn].

| Command | What it does |
|---|---|
| `driver status` | Read-only, no admin, no MIDI sent. Prints the live position, the stacks, the port names, the scoreboard, and "firmware updates: OK here / go home first". `--live` adds a Device Inquiry |
| `driver go class` / `go class-new` / `go winusb` | Admin only; never elevates itself; refuses unless the KeyLab is at home |
| `driver home` | `DiInstallDevice(parent, no driver)`, so Windows chooses by rank |
| `--dry-run` | Prints the driver it would select, and calls nothing |

**How it picks a driver** [I; S: Learn for the calls]:
1. `SetupDiOpenDeviceInfoW` on the instance ID.
2. `SetupDiBuildDriverInfoList(SPDIT_COMPATDRIVER)`.
3. Choose an entry by its original INF name, provider and matched ID.
4. `DiInstallDevice(…, DIIDFLAG_NOFINISHINSTALLUI, &needReboot)`.
5. Wait up to 30 s with `CM_WaitNoPendingInstallEvents`.
6. Run the checks.

**Each switch, and its manual fallback in Device Manager:**

| Switch | Tool action | Manual fallback |
|---|---|---|
| 1 → 2-classic | `DiInstallDevice(parent, usb.inf "USB Composite Device")`; the `MI_00` child then installs by itself | "Arturia USB MIDI Devices" → KeyLab 88 mk3 → Update driver → Browse → Let me pick → "USB Composite Device" |
| 2-classic → 2-new | `DiInstallDevice(MI_00, usbmidi2.inf)` | Sound, video and game controllers → KeyLab 88 mk3 → … → "USBMidi2-ACX" |
| 2 → 1 | `DiInstallDevice(parent, NULL)` → Arturia by rank; its KS child returns through oem11 | Universal Serial Bus controllers → the "USB Composite Device" whose Details show `VID_1C75&PID_02CE` → … → "KeyLab 88 mk3" |
| 1 → 3a | Guided: the tool runs preflight and pauses; you pick; the tool writes `DeviceInterfaceGUIDs`, restarts the device and checks liveness | Let me pick → Universal Serial Bus devices → "WinUsb Device" → accept the warning |
| 3 → 1 | Stop our program, `DiInstallDevice(parent, NULL)`, delete `DeviceInterfaceGUIDs` | As 2 → 1 |
| Last-resort home | `pnputil /remove-device <id>` then `pnputil /scan-devices` | Uninstall device (leave "delete the driver" **unticked**) → Scan for hardware changes |

**Preconditions (the tool refuses if any fails).** Each one is a chapter in action.
1. Running elevated.
2. The KeyLab is present, started and has no problem code.
3. The current position is known and the move is allowed by the star.
4. Home is safe: Arturia is "Best Ranked", and any package of ours is "Outranked".
5. The target package is in the store, found by original name.
6. FL, Analog Lab, MIDI Control Center, Arturia Software Center and its Agent are all closed.
7. No `arsenal.keylab` process is running.
8. No reboot is pending.
9. The KeyLab answers before the switch. A KeyLab that is already hung is not switched; run the hang ladder instead, or the driver gets blamed for a firmware fault.
10. For 3b: the setup receipt exists.

**Liveness after a switch:**
- **Positions 1 and 2:** send one Device Inquiry `F0 7E 7F 06 01 F7` from a worker thread with a 2 s deadline, and listen on every KeyLab input for 1.5 s for a reply starting `F0 7E xx 06 02 00 20 6B` [S: G2].
- **Position 3:**
  1. `WinUsb_Initialize` succeeds.
  2. The device descriptor returns 18 bytes with idVendor 0x1C75, idProduct 0x02CE and bcdDevice 0x1500.
  3. The configuration descriptor parses into interfaces and endpoints.
  4. The bus speed is read.
  5. Optionally, the inquiry is sent as raw packets `14 F0 7E 7F | 17 06 01 F7` [S: L12; I].

  The first visit to position 3 is therefore also the descriptor read every lane has been waiting for.

**Receipts.** One JSON file per switch goes to `state/arsenal/keylab/receipts/driver-<from>to<to>-YYYYMMDD-HHMMSS.json`, marked class **eyes** when you watched. It records:
- before and after: stacks, INFs, ranks and port names;
- the call made, `needReboot` and the duration;
- the setupapi section for the switch;
- the liveness result;
- the verdict.

**Automatic rollback to Arturia.**
- **Triggers:** `DiInstallDevice` fails; a reboot is reported as needed; installs are still pending after 30 s; the wrong driver or a problem code appears; or liveness fails.
- **Action:** go home by rank, remove any `DeviceInterfaceGUIDs` we added, check liveness, write the receipt.
- **If home's own liveness fails,** the tool prints the human ladder: replug → Let me pick "KeyLab 88 mk3" → Uninstall (driver kept) + Scan → reboot. The last resort is Arturia's installer, already on disk, which only you run.
- **Drill doctrine:** a `--inject-liveness-failure` flag forces a rollback, so the rollback path earns its own dated receipt before anyone trusts it.

### L6. The first experiment: 1 → 2 → 1, by hand, with you present

About 40 minutes. Device Manager plus the read-only Looks you already know. No code is built and nothing is downloaded. It is one Forest Walk: predict, do, look, teach back.

**Stage 0: prepare (10 min)**
1. Close FL. Quit Analog Lab, MIDI Control Center, Arturia Software Center **and its tray Agent**, and any `arsenal.keylab` process (`vj --no-leds` was running on 10-27).
   - *What this teaches (chapters 2 and 3):* before Windows swaps a function driver, it asks every program holding the device to let go (the "query-remove" handshake). A program that refuses forces a reboot.
2. Open an admin Terminal, used for looking only, and save three snapshots:
   - `pnputil /enum-devicetree "USB\VID_1C75&PID_02CE\7656400341020110" /stack /drivers` as `before.txt`;
   - `pnputil /enum-devices /instanceid "USB\VID_1C75&PID_02CE\7656400341020110" /drivers`;
   - `py -m arsenal.keylab ports`.
3. Check liveness with the guide's Device Inquiry check, or `py -m arsenal.keylab monitor` and a pad press.
4. **Write down your predictions:**
   - **P1 (chapter 5):** which driver will Windows put on the MIDI part, usbaudio or USBMidi2?
   - **P2 (chapter 8):** how many `MI_xx` children appear, and with which interface classes?
   - **P3 (chapter 3):** will the switch need a reboot? The 06-11 precedent says no.
   - **P4 (chapter 10):** what will the port names be?
   - **P5 (chapter 9):** will the KeyLab answer the inquiry on Microsoft's driver?
   - **P6 (chapter 10):** after returning home, will the names and the endpoint ID be identical?

**Stage 1: go to position 2 (10 min)**
1. In Device Manager: "Arturia USB MIDI Devices" → KeyLab 88 mk3 → Update driver → Browse my computer → Let me pick → **"USB Composite Device"** → Next.
   - *Teaches chapter 3:* only the top of the KeyLab node's stack changes, from arturiausbmidi to usbccgp, while `ACPI | USBHUB3` stays. usbccgp now acts as a bus driver and invents `MI_xx` children, just as Thesycon invented its KS child.
2. Look:
   - Save the device tree as `pos2.txt`.
   - **Answers P1 (chapter 5):** run `pnputil /enum-devices /instanceid "<MI_00 id>" /drivers` to see the child's own scoreboard, with "Best Ranked" and the rank values in plain text.
   - **Answers P2 (chapter 8):** read each `MI_xx` child's compatible IDs. Class 01 is audio or MIDI; FE/01 would be a firmware-update interface [S: USB DFU class; I]. This is the KeyLab's interface layout, printed by Windows, with no descriptor tool.
   - Read the newest "Select Drivers" block at the end of `C:\Windows\INF\setupapi.dev.log`: the same scoreboard the 06-11 log printed.
3. Liveness:
   - **Answers P5 (chapter 9):** send the inquiry on each KeyLab output, listening on both inputs.
   - Press a key and a pad into `monitor --port "<new name>"`. Use an explicit `--port`, because of the `_match` trap from chapter 10.
   - **Answers P4 (chapter 10):** note the new names. Under Windows MIDI Services' naming rules they may be classic ("MIDIOUT2 (…)") or the device's own iJack names [S: naming KB, fetched].
4. **Stop rule:** no reply → one unplug and replug (Microsoft's own step) → still nothing → go straight to Stage 2.
5. **Optional, your call:**
   - (a) Open MIDI Control Center only to see whether it finds the KeyLab. Never click update.
   - (b) Switch `MI_00` to USBMidi2-ACX. I'd keep this for a second walk, so each session changes only one thing.

**Stage 2: go home (5 min)**
1. In Device Manager: Universal Serial Bus controllers → the KeyLab's "USB Composite Device" (Details → Hardware Ids shows `VID_1C75&PID_02CE`) → Update driver → Let me pick → **"KeyLab 88 mk3"** → Next.
   - *Teaches chapter 5:* the scoreboard puts Arturia back. Going home needed no download and no judgement.
2. Look:
   - Compare the tree with `before.txt`.
   - **Answers P6 (chapter 10):** run `ports` and compare the names, and compare the midisrv endpoint ID.
   - Run the inquiry.
   - *Teaches chapter 2:* midisrv kept running the whole time and simply rebuilt its endpoint.
3. Restart the house's KeyLab services, then open FL. Does its saved KeyLab setup still work untouched?
4. **If home fails,** climb the ladder: replug → pick Arturia again → Uninstall device (driver kept) + Scan for hardware changes → reboot → Arturia's installer, which you run yourself.

**Stage 3: receipt and teach-back (10 min)**
- Write a dated **eyes**-class receipt by hand, with the same fields the tool will later write.
- **Teach-back prompts:**
  - "Why did going home need no download and no choice?" (chapter 5)
  - "Which driver created each node's bottom layer, before and after?" (chapter 3)
  - "Why did FL have to be closed?" (chapters 2 and 3)
  - "What did the `MI_xx` IDs tell us about the KeyLab?" (chapter 8)
  - "Every driver we touched was in-box or attested. What would position 3b have changed about trust?" (chapter 6)
  - "Which prediction did you get wrong, and what did the scoreboard say instead?"

### L7. What each program sees in each position

| | **1. Arturia** | **2. Microsoft class** | **3. WinUSB + ours** |
|---|---|---|---|
| **FL Studio** | "KeyLab 88 mk3 MIDI" and "…DAW", in and out [S:local]. Arturia's FL script binds by Device Inquiry [S: guide] | Names follow Windows MIDI Services' rules [S: naming KB, fetched]. If they differ, FL's port setup and the script need redoing, as happened to users on usbaudio [S: Image-Line forum, via the driver study] | Only our ports, present only while our program runs [S: M3]. Named like position 1, so FL's settings carry over [I] |
| **Analog Lab V** | Works. It needs the exact Windows names for its screen and buttons [S: forum t/5294] | Notes flow; screen integration depends on the names [I] | Through our ports; depends on names and on SysEx passing through untouched [I] |
| **MIDI Control Center** | Sees the device; firmware updates through Thesycon's update calls [S:local strings] | Likely no device and no updates [I] | No device [I] |
| **House tools** | As today | Use an explicit `--port`, or keep them stopped (the `_match` trap) [S:local code] | They talk to our program |
| **midisrv endpoint** | `MIDIU_KSA_16201702556534547415` [S:local] | A new endpoint ID [I] | Our Virtual Device |

### L8. Risks and their guards

| Risk | Guard |
|---|---|
| A program holds the device during a switch, so a reboot would be needed [S: Learn] | Preflight process checks. A needed reboot counts as failure and sends the KeyLab home |
| A half-finished switch (parent moved, child failed) | Settle wait, child checks, automatic return home |
| A firmware update in the wrong position | Updates only from position 1. Preflight refuses while MCC runs. `status` says "go home first" |
| Port names change in position 2 | Receipts record the names; use explicit `--port`; the experiment measures it |
| Windows reverts the choice (the PnP bug, Windows Update, Arturia's installer) | That is the safe direction. `status` flags the drift [S: M1; S:local 06-11] |
| A package of ours outranks Arturia's | Empty hardware-ID slot plus an old date; checked "Outranked" after staging, or deleted at once |
| USBMidi2's 15-minute idle sleep | Use usbaudio for A/B work; note it in receipts |
| The 3b root certificate | Key destroyed after one signature; thumbprint recorded; removal steps written; your call |
| Our program dies in position 3 | A supervisor; `driver home` always works |
| A needed reboot | After a reboot the house's Aurora tasks must be started by hand; switch only when a reboot is acceptable |

### L9. After the experiment

**Build order [I]:**
1. `driver status` (read-only).
2. Switching 1↔2 with the helper, plus the rollback drill.
3. 3a binding plus the WinUSB descriptor liveness check, alongside the hub's WinUSB layer.
4. 3b, only if you want it.

**Open questions, and which step answers each:**

| Question | Answered by |
|---|---|
| Which Microsoft driver does Windows pick, and how many interfaces does the KeyLab have? | Stage 1 |
| Does a switch complete without a reboot while midisrv runs? | P3 |
| Do port names and FL's setup survive the round trip? | Stages 1 and 2 |
| Does MCC need Arturia's driver to see the device at all? | Optional probe (a) |
| Does the revision 0500 updater identity keep the serial number? | `driver status` before and after the next firmware update |
| Does WinUSB on the whole device expose the MIDIStreaming pipes? | The first 3a visit |

### Elective, for later: write your first driver, safely [I]

If the course leaves you wanting to *write* a driver, not only read one, the safe sandbox is a Windows 11 virtual machine:
- Hyper-V is part of Windows 11 Pro; turning it on is a system change and your call.
- Inside the VM, Secure Boot can be off and test signing on, while the music PC's own Secure Boot stays untouched.
- A blue screen then takes down only the VM.
- The classic first project is Microsoft's "Write a Hello World Windows Driver (KMDF)". After that, read the KMDF USB sample (`usb/kmdf_fx2` in microsoft/Windows-driver-samples), then fork nothing until it all makes sense.
- Downloads (Visual Studio + WDK, and a Windows VM image) are several GB each [I]; they are listed in the approvals section. Not before the capstone.

---

## Glossary

- **ACPI**: the firmware's description of the board. It appears in stacks as a filter that supplies location and power data, outside the data path.
- **ACX**: Microsoft's newer audio framework, built on KMDF. USBMidi2 uses it.
- **Attestation signing**: the vendor proves its identity with an EV certificate, and Microsoft signs without full lab testing. "Universal, Attested" on Arturia's packages.
- **AVStream / KS (kernel streaming)**: the kernel framework for audio and MIDI data pins. `arturiausbmidiks.sys` is an AVStream minidriver.
- **Bugcheck**: a deliberate system stop (blue screen) after a kernel fault. 0x9F and 0x133 are this PC's two.
- **Bus driver**: the driver that creates a node, its PDO, at the bottom of the stack.
- **Catalog (CAT)**: a signed list of hashes for every file in a driver package.
- **CIN (Code Index Number)**: the low nibble of a USB-MIDI packet's first byte; the message's type and length tag.
- **Compatible ID**: a generic "feature flag" ID, such as `USB\Class_01`. It scores worse than a hardware ID.
- **Composite device**: a USB device with several interfaces in one configuration (`USB\COMPOSITE`). Windows normally splits it with usbccgp.
- **Descriptor**: the data a USB device hands the host to describe itself (device, configuration, interface, endpoint).
- **Device interface**: a named "door" a driver publishes so programs can open the device, identified by a GUID.
- **Device node / device stack**: one entry in the device tree, and the drivers layered on it.
- **DFU (Device Firmware Upgrade)**: the USB class for firmware updates. Arturia's INF sets `DFUProtocol=2`.
- **DMA**: a device reading or writing RAM by itself.
- **DPC / ISR**: interrupt work split into a minimal handler (the ISR, at device IRQL) and deferred work (the DPC, at DISPATCH).
- **DriverStore**: Windows' shelf of installed driver packages; drivers run straight from it.
- **Endpoint**: a one-way USB mailbox (bulk, interrupt, isochronous or control).
- **FDO / PDO**: the function driver's device object, and the physical device object created by the bus driver.
- **Filter driver**: a layer above or below the function driver, such as ksthunk.
- **Function driver**: the driver that owns a device's behaviour; the top of its stack.
- **Hardware ID**: the most specific ID, such as `USB\VID_1C75&PID_02CE&REV_1500`.
- **INF**: a driver package's install recipe. Stored copies are renamed `oemNN.inf`.
- **IRP**: an I/O Request Packet, passed down a stack and completed back up.
- **IRQL**: interrupt request level: PASSIVE, DISPATCH, DIRQL.
- **KMDF / UMDF / WDM**: the kernel framework, the user-mode framework, and the raw hand-written model underneath them.
- **KSA**: midisrv's KS-aggregate transport, which presents all of a device's pins as one endpoint.
- **midisrv**: the Windows MIDI Services service, a user-mode process that owns and shares every MIDI device.
- **MSI / MSI-X**: an interrupt delivered as a memory write over PCIe.
- **NAK**: a USB handshake meaning "not ready". Flow control, not an error.
- **Rank**: Windows' driver score, `0xSSGGTHHH`; lower wins.
- **Secure Boot**: the firmware-to-kernel chain of trust. On for this PC.
- **Test signing**: a boot mode that accepts any certificate. Blocked while Secure Boot is on.
- **UCX**: the USB controller extension, a KMDF helper under USBXHCI.
- **UMP**: Universal MIDI Packet, MIDI 2.0's fixed-width packet format.
- **URB**: USB Request Block, the request a USB driver hands the hub.
- **usbccgp / usbaudio / USBMidi2**: Microsoft's composite splitter, its classic USB audio and MIDI driver, and its new MIDI driver.
- **WinMM**: the classic Windows MIDI API (winmm.dll) that FL uses.
- **WinUSB**: Microsoft's generic USB driver that hands a device's pipes to a program.
- **xHCI**: the USB host controller standard, built from transfer rings, doorbells and an event ring.

---

## Reading list, in course order

Grades: "fetched" pages were read by a lane on 10-26 or 10-27. The rest are standard references, not fetched tonight; check that each link still resolves.

**Start here (week 1)**
- Microsoft Learn, "Getting started with Windows drivers". Read "What is a driver?", "User mode and kernel mode", "Device nodes and device stacks", "I/O request packets" and "Driver stacks", under https://learn.microsoft.com/en-us/windows-hardware/drivers/gettingstarted/ (chapters 1-3).
- Ben Eater's videos "How does a USB keyboard work?" and "How does USB device discovery work?" on YouTube. Hardware-first, oscilloscope on the wire: your register (chapters 4 and 8).
- "USB in a NutShell", beyondlogic.org: https://www.beyondlogic.org/usbnutshell/ (chapter 8).

**Kernel mechanics (chapters 2-4)**
- Learn, "Managing hardware priorities" (IRQLs) and "Introduction to DPC objects", under https://learn.microsoft.com/en-us/windows-hardware/drivers/kernel/
- Learn, "Introduction to message-signaled interrupts" (same section).
- Learn, Timeout Detection and Recovery: https://learn.microsoft.com/en-us/windows-hardware/drivers/display/timeout-detection-and-recovery
- Learn, Bug Check 0x9F and Bug Check 0x133, under https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/

**Driver choice and packages (chapters 5 and 6)**
- Learn, "How Windows ranks driver packages", "Identifier score", "Signature score" and "Overview of the driver package selection process" (all fetched), under https://learn.microsoft.com/en-us/windows-hardware/drivers/install/
- Learn, "Driver signing policy" (kernel-mode code signing) and "The TESTSIGNING boot configuration option" (fetched), same section.
- Learn, "PnP device installation signing requirements" (fetched), same section.
- Learn, "Run from Driver Store": https://learn.microsoft.com/en-us/windows-hardware/drivers/develop/run-from-driver-store
- Learn, `DiInstallDevice` (fetched): https://learn.microsoft.com/en-us/windows/win32/api/newdev/nf-newdev-diinstalldevice

**Frameworks (chapter 7)**
- Learn, "Choosing a driver model", and "Write a Hello World Windows Driver (KMDF)", under the gettingstarted path.
- github.com/microsoft/Windows-driver-samples: `usb/kmdf_fx2` (a complete KMDF USB driver) and `usb/usbview` (the source of the USBView already on your disk).

**USB (chapters 8 and 9)**
- Learn, "USB generic parent driver (usbccgp)", "Enumeration of USB composite devices" and "Support for interface collections" (fetched), under https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/
- Learn, "Standard USB identifiers": https://learn.microsoft.com/en-us/windows-hardware/drivers/install/standard-usb-identifiers
- Learn, "How to capture a USB event trace" (the built-in logman trace), under usbcon.
- **USB-IF specifications:**
  - USB Device Class Definition for MIDI Devices 1.0: https://www.usb.org/sites/default/files/midi10.pdf (§4 and Table 4-1 are chapter 9);
  - USB 2.0 specification, chapters 5, 8 and 9: https://www.usb.org/document-library/usb-20-specification;
  - USB Audio 1.0 and DFU 1.1, in the usb.org document library;
  - USB MIDI 2.0 class definition, usb.org.
- Intel, eXtensible Host Controller Interface (xHCI) 1.2: transfer rings, doorbells and event rings (chapter 4).
- Code to read alongside the spec: Linux's `sound/usb/midi.c` (github.com/torvalds/linux) and TinyUSB's `src/class/midi/midi.h` (github.com/hathach/tinyusb).

**MIDI on Windows (chapter 10)**
- Windows MIDI Services docs and KB (fetched): https://microsoft.github.io/MIDI/, especially "How to switch between MIDI class drivers", "Kernel streaming aggregate", "Virtual Device App" and "MIDI 1.0 name mapping".
- github.com/microsoft/MIDI: the USBMidi2 driver source at `src/in-box/Drivers/USBMIDI2` (MIT; a real KMDF + ACX driver to read) and `src/in-box/Libs/MidiKs/MidiKs.cpp` (the service's write path and its upstream timeout fix).

**Userspace drivers (chapter 11)**
- Learn, "Introduction to WinUSB for developers", "WinUSB (Winusb.sys) installation" (fetched), "WinUSB functions for pipe policy modification" and "How to recover from USB pipe errors", under usbcon.
- libusb: https://libusb.info and the Windows wiki page, https://github.com/libusb/libusb/wiki/Windows
- libwdi FAQ (fetched): https://github.com/pbatard/libwdi/wiki/FAQ
- Precedents: github.com/Ableton/push-interface (Push 2's display through libusb) and github.com/mayerwin/Perfect-Bluetooth-MIDI-For-Windows (a Windows MIDI Services Virtual Device bridge) [S: driver study].

**Books (to buy)**
- *Windows Internals*, 7th ed., Part 1 (Yosifovich, Ionescu, Russinovich, Solomon), chapter 6, "I/O system". This is the course's backbone. Part 2 covers interrupts, IRQL and DPCs in its system-mechanisms chapter [I for the Part 2 chapter].
- Pavel Yosifovich, *Windows Kernel Programming*, 2nd ed. The friendliest route to writing kernel code.
- Jan Axelson, *USB Complete*, 5th ed. USB from the wire up, device side and host side.
- Penny Orwick and Guy Smith, *Developing Drivers with the Windows Driver Foundation* (Microsoft Press). The KMDF/UMDF design rationale.
- Walter Oney, *Programming the Microsoft Windows Driver Model*, 2nd ed. The WDM classic, which is the model Thesycon's driver is written in.
- Corbet, Rubini and Kroah-Hartman, *Linux Device Drivers*, 3rd ed., free at lwn.net/Kernel/LDD3/. Another OS, the same ideas; its USB chapter pairs well with chapter 8.

**Talks and community**
- OSR (osr.com): *The NT Insider* articles and the NTDEV forum, where Windows driver writers argue in public.
- Pavel Yosifovich's talks and recordings on Windows internals (YouTube).

---

## Downloads and runs that need your approval (none done)

| # | What | Source | Size | Status | Why, and the risk |
|---|---|---|---|---|---|
| 1 | The 1 → 2 → 1 experiment | In-box drivers | Nothing to download | Your go | A driver switch is a system change: admin, FL and Arturia's apps closed |
| 2 | **Run USBView** to read the KeyLab's descriptors and bus speed | **Already on this PC:** `C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\usbview.exe`, Microsoft-signed, 10.0.26100.7705; also `usbview2.exe` "USB Device Viewer 2" [S:local] | 842,072 B (usbview.exe); 1,169,776 B (usbview2.exe) | A run approval, not a download | It sends descriptor requests to the KeyLab through the hub [I; S: driver study]. Run it only with FL closed. The lab's Stage 1 answers most of the same question for free |
| 3 | Built-in USB trace (`logman`, rundown plus bus events) | Built into Windows | Trace size not measured | Admin | Descriptors and bus speed from Windows' cached data (no bus traffic is my inference), and at the next hang, which end stuck [S: driver study] |
| 4 | **Read the two minidumps** with the debugger | **Already on this PC:** `cdb.exe` (178,536 B), `windbg.exe` (604,520 B) and `kd.exe` (207,192 B), same folder, Microsoft-signed, 10.0.26100.7705 [S:local] | Symbol files from Microsoft's public symbol server (`https://msdl.microsoft.com/download/symbols`) are needed and cached locally; size not checked | Approval for the symbol download | Names the drivers behind 0x133 and 0x9F. Reading `C:\Windows\Minidump` may need admin. The modern WinDbg app (Microsoft Store, or `winget install Microsoft.WinDbg`) is optional; size not checked |
| 5 | Windows MIDI Services Tools, preview 12 (x64) | github.com/microsoft/MIDI releases, tag inbox-preview-12 | 223,376,824 B [S: driver study] | Needed for position 3's ports and the troubleshooter's switch button | A preview; it also installs the Windows App SDK runtime |
| 6 | Specification PDFs: USB-MIDI 1.0, USB 2.0, USB Audio 1.0, DFU 1.1, USB MIDI 2.0, xHCI 1.2 | usb.org; intel.com | Not checked | Reading only | None |
| 7 | Position 3a binding | In-box `winusb.inf` | — | After the experiment | Adds a `DeviceInterfaceGUIDs` value under Device Parameters |
| 8 | Position 3b: a root certificate plus our package | Tools already on disk (makecat, signtool, New-SelfSignedCertificate) [S:local] | — | Only after living with 3a | A machine-wide trust change |
| 9 | A .NET SDK, only if Python can't reach the Virtual Device SDK | Microsoft | Not checked | Only if needed [I] | None beyond disk space |
| 10 | Elective: Visual Studio + WDK, Hyper-V, and a Windows 11 VM image | Microsoft | Several GB each [I] | After the capstone | Turning on Hyper-V is a system change. Test signing stays inside the VM |
| — | Not recommended | USBPcap 1.5.4.0 (195,040 B; installs a kernel filter driver, and logman covers it); Thesycon `tdd.exe` (vendor binary, no longer needed now that USBView is on disk); Zadig (its own root certificate and INF rank) | — | — | — |

---

## What this assembly did

- **Read in full:** `research/reviewed/keylab-liberation-2026-10-22/keylab-driver-study-2026-10-27.md` (944 lines), plus the three verbatim inputs: the curriculum, the machine walk and the toggle design.
- **Re-checked, read-only, on 2026-10-27:**
  - the version and signer of five Debuggers-folder tools, which is how USBView and WinDbg turned up on disk;
  - the minidump listing;
  - the KeyLab's hardware IDs, compatible IDs, capabilities and location paths;
  - a `WDFLDR.SYS` text search in six driver binaries;
  - the user-mode chain versions and midisrv's start time;
  - the xHCI's MSI flag;
  - the `usbflags` osvc values;
  - Secure Boot, Device Guard and the blocklist;
  - the catalog signature and size;
  - the KeyLab's {A5DCBF10} interface;
  - pnputil's `/enum-devices` switches.
- **Ran** a 7-line USB-MIDI packet packer from the scratchpad (`<scratch>\pack.py`). It is pure arithmetic and imports no repo code.
- **Not done:** no KeyLab port or USB handle opened, FL untouched, no vendor binary run, nothing installed, switched or downloaded, no repo edits.
- **One slip against the brief:** a single Bash call ran `cd` into `C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\` to list files. It was read-only and changed nothing, but it did leave the repository directory, which the brief forbids. Every later command used absolute paths.

---

## Sources

**Microsoft Learn (learn.microsoft.com/en-us/windows-hardware/drivers/…)**
- **Fetched:**
  - L1 Identifier Score
  - L2 Signature Score
  - L4 USB Generic Parent Driver
  - L5 Enumeration of USB composite devices
  - L6 Driver Signing Policy
  - L7 the test-signing pages
  - L8 PnP Device Installation Signing Requirements
  - How Windows Ranks Driver Packages
  - Overview of the Driver Package Selection Process
  - Support for Interface Collections
  - WinUSB installation
  - DiInstallDevice
  - UpdateDriverForPlugAndPlayDevicesW
- **Cited, not fetched:**
  - L3 ranking tie-breaks
  - L9 Bug Check 0x9F
  - L10 Bug Check 0x133
  - L11 Standard USB identifiers
  - L12 WinUSB and pipe policies
  - L13 Choosing a driver model / UMDF
  - L14 IRQLs, ISRs, DPCs
  - L15 What is a driver, stacks, IRPs
  - L16 Run from Driver Store
  - L17 WDDM and TDR
  - L18 Message-signalled interrupts
  - the ACX overview
  - `CM_WaitNoPendingInstallEvents`

**Windows MIDI Services KB (microsoft.github.io/MIDI/kb/…)**
- **Fetched:**
  - M1 how-to-switch-between-class-drivers
  - M2 kernel-streaming-aggregate
  - M3 virtual-device-app
  - M4 the KB index
  - midi1-name-mapping

**Other pages and specifications**
- **Fetched:**
  - T1 thesycon.de/eng/usb_audiodriver.shtml
  - P1 pci-ids 1022:43fd and 1022:43f5
  - Z1 the libwdi FAQ
- **Not fetched:**
  - U1 USB 2.0 Specification
  - U2 USB Device Class Definition for MIDI Devices 1.0
  - U3 USB MIDI 2.0
  - X1 xHCI 1.2
  - B1 *Windows Internals*, 7th ed.
  - the USB DFU class

**Local, read-only (this PC)**
- Device properties, pnputil output and the registry.
- INFs: oem22, oem11, usbmidi2, wdma_usb, winusb, usb, c_midi, c_swdevice.
- `C:\Windows\INF\setupapi.dev.20260715_043401.log` (lines 4505-4591 and 7442-7711) and `setupapi.dev.20260214_034609.log` (line 46844).
- The Windows SDK 10.0.26100.0 headers and the Debuggers folder.

**Our own documents**
- G1: `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-hang-study-2026-10-26.md`
- G2: `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-dev-guidance-and-hang-guide-2026-10-27.md`
- The driver study: `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-driver-study-2026-10-27.md`
- `E:\AI-Setup\arsenal\keylab\protocol.py`, `E:\AI-Setup\arsenal\keylab\winmidi.py` and `E:\AI-Setup\arsenal\keylab\README.md`

---

## The toggle design (verbatim)

# The KeyLab driver toggle: a three-position design, and a first experiment Daniel can run by hand (2026-10-27, design only)

**Answer:** yes, the toggle can be built. All the drivers live on this PC at the same time, and only one drives the KeyLab at any moment. A switch tells Windows which stored driver to attach to the KeyLab's device node.

- **Positions 1 and 2 need no download.**
- **Position 1 is Arturia's driver (Thesycon).** It is "home": every switch starts there and returns there, and any failure sends the KeyLab back there automatically.
- **Position 2 is Microsoft's in-box class driver.**
- **Position 3 is Microsoft's signed WinUSB driver plus a program of ours.** That program is the "userspace driver". No kernel code of ours is involved, so Secure Boot is untouched.

**Grades:**
- **[S]** a cited source says it ("fetched" means read tonight).
- **[S:local]** measured read-only on this PC tonight.
- **[I]** my inference.

---

## In one minute

- **One Windows call does every switch.** `DiInstallDevice` installs a named, already-stored driver on one device [S: Learn DiInstallDevice, fetched]. Called with no driver named, it installs "the driver that is the best match" from the store [S: same]. On this PC that is Arturia's, ranked `00FF0001` and "Best Ranked" [S:local]. So "go home" works like Load Optimized Defaults in a BIOS: Windows' own scoreboard makes the choice.
- **pnputil can't do the switch.** It has no verb that puts a chosen driver on a chosen device [S:local `pnputil /?`].
- **`UpdateDriverForPlugAndPlayDevices` is the wrong tool.** It wants the INF outside `%SystemRoot%\inf`. With FORCE, it updates every device that matches the ID you give it [S: Learn, fetched]. Matching on `USB\COMPOSITE` would hit the webcam, the NZXT mic and the RGB controller too [S:local].
- **Position 2 binding.** The KeyLab's parent node gets "USB Composite Device" (usbccgp). Windows should then put usbaudio.sys on the MIDI part by itself, and USBMidi2-ACX takes a second, explicit pick [I, from the rank rules; the machine walk's correction].
- **How Microsoft says to move a device between its two drivers:**
  - Device Manager, "Update driver → Browse my computer → Let me pick". Then choose "USB Audio Device" or "USBMidi2-ACX".
  - Or the MIDI Troubleshooting and Repair app.
  - Close your DAW first. Afterwards, "unplug the device, restart your PC, and plug the device back in" [S: M1, fetched].
- **Position 3 binding.** WinUSB goes on the whole KeyLab, the same node Arturia's driver holds today [I]. Two ways to bind it:
  - **3a (recommended first):** pick Microsoft's own "WinUsb Device" by hand. It is Microsoft-signed, so trust settings don't change [S: Learn winusb-installation, fetched].
  - **3b:** our own INF, with a catalog signed by a certificate made once and then thrown away, as libwdi/Zadig do. This gives one-command switching, but it adds a root certificate to the machine, which is Daniel's call [S: libwdi FAQ, fetched].
  - Our INF would sit one rung below Arturia's on Windows' scoreboard, so Windows never picks it by itself [I, from the rank rules].
- **New measurements tonight:**
  - **Arturia's own installer did this exact switch on this PC.** On 2026-06-11 it removed the old driver, staged the new package and installed the best-ranked driver. The KeyLab was re-driven live in under a second, with no reboot [S:local setupapi.dev.log].
  - **A firmware update did not make Windows pick a driver again.** Firmware 1.5.0 first appeared 20 minutes after that driver install, and nothing was reinstalled [S:local].
  - **Programs are holding Arturia's driver right now:**
    - Arturia Software Center and its tray Agent are running; the Agent links Thesycon's API [S:local; driver study].
    - Our own `arsenal.keylab vj` is running [S:local].

    All of them must close before any switch.
- **First experiment: 1 → 2 → 1, by hand in Device Manager, with Daniel present.** It takes about 40 minutes, needs no new code, and every step can be undone. It would settle three things:
  - which Microsoft driver Windows actually picks, read off Windows' own scoreboard (the course and the machine walk disagree on this);
  - the KeyLab's USB interface classes, read without a descriptor tool;
  - whether FL's port names come back unchanged.

---

## What I did (all read-only)

**Read:**
- The driver study (all 945 lines), the curriculum and the machine walk.
- The setupapi device-install logs, using targeted greps and three excerpts.
- The `usbflags` registry keys and their last-write times.
- The Kernel-PnP configuration event log.
- The in-box `winusb.inf`.
- `pnputil /?`.
- The running processes, by name and command line only.
- The Arturia and FL executable folders, and which signing tools the installed Windows SDK holds.
- `arsenal/keylab/winmidi.py`.

**Fetched (8 pages):** M1, UpdateDriverForPlugAndPlayDevices, DiInstallDevice, WinUSB installation, the libwdi FAQ, PnP signing requirements, the MIDI 1.0 port-naming KB and the Virtual Device App KB.

**Did not do:**
- open any KeyLab port or USB handle, or touch FL;
- run any vendor binary;
- install, switch, change or download anything;
- edit the repo, or leave it.

One small in-memory C# helper read registry key timestamps.

---

## 1. What tonight's reading adds

### 1.1 Arturia's installer already performs this toggle on this PC [S:local, `setupapi.dev.20260715_043401.log`]

On 2026-06-11 the 1.6.0.0 → 1.7.0.0 update did the following:

| Time | Step | What it is |
|---|---|---|
| 21:31:41 | `DiUninstallDevice` on the KS child | It first removed midisrv's endpoint and the four WinMM nodes, then the child ("Query-and-Remove succeeded"). midisrv let go without any fuss |
| 21:31:42 | `DiInstallDevice` with "Installing NULL driver" on the KeyLab | The `DIIDFLAG_INSTALLNULLDRIVER` path [S: Learn] |
| 21:31:47 | `SetupUninstallOEMInf - oem64.inf` | The old 1.6.0.0 package deleted |
| 21:32:03 | `DiInstallDriver` stages the new packages as `oem22`/`oem11` | |
| 21:32:04 | "Installing best driver (oem22.inf)" | The scoreboard printed in the log: oem22 rank `00FF0001`, "Selected"; usb.inf "USB Composite Device" `00FF2006`, "Outranked" |

- The device restarted between 21:32:04.305 and .736. There is no reboot line.
- **Lesson 1:** a live switch completes here with midisrv running.
- **Lesson 2:** `oemNN` numbers get recycled. The tool must find Arturia's package by its original name, `arturiausbmidi.inf`, never by "oem22". (The brief's "oem41" was already wrong tonight.)
- At that time the KeyLab sat behind a Realtek hub (`USB\VID_0BDA&PID_5411`). Its instance ID, which is its serial number, carried the driver choice to port 8 [S:local].

### 1.2 The firmware-update timeline [S:local, last-write times of `usbflags` keys, local time]

| Key | Last written | Reading |
|---|---|---|
| `1C7502CE0500` | 2026-01-24 20:28:21 | An "updater" identity: same product ID, REV 0500 [I] |
| `1C7502CE1201` | 2026-01-24 20:35:42 | Firmware 1.2.1, 7 minutes later: one update session [I] |
| `1C7502CE1500` | 2026-06-11 21:52:39 | Firmware 1.5.0, 20 minutes after the driver update [I] |
| `1C7502CE1101`, `1C75021B0100`, `1C7502CB0200` | 2025-11-02 01:32:28 | All in the same second: a bulk rewrite, not arrivals [I] |

- **A firmware update doesn't re-trigger driver choice.** No setupapi install section for the KeyLab exists after 21:32:04 on 06-11, so the REV change to 1500 did not make Windows pick again [S:local; I, strong].
- **Once, the KeyLab showed up without its serial number.** An instance with a port-based ID, `USB\VID_1C75&PID_02CE\8&D1AFB05&0&4`, existed until Storage Sense deleted it on 2026-01-28 [S:local]. The 01-24 updater mode is the likeliest moment [I].
- **That would be a brand-new device to Windows.** It would remember no driver choice, so Windows binds it by rank: Arturia, as long as Arturia's package is in the store and stays best-ranked [I].
- **Consequences for the design:**
  - Never delete Arturia's packages.
  - Never let a package of ours outrank Arturia's for `VID_1C75&PID_02CE`.
  - Firmware updates start only in position 1.

### 1.3 What holds the KeyLab right now [S:local, process list]

- `Arturia Software Center` (pid 61268) and `ArturiaSoftwareCenterAgent` (pid 51992), both started 10-23 09:51. The Agent links Thesycon's API wrapper [S: driver study].
- `py -m arsenal.keylab vj --no-leds --quiet` (pids 8112 and 47992).
- `MidiSrv` (pid 45480).
- FL, Analog Lab and MIDI Control Center are not running.

### 1.4 Tools already on disk [S:local]

- In the Windows SDK 10.0.26100.0, x64: `makecat.exe`, `signtool.exe`, `MakeCert.exe`.
- PowerShell: `New-SelfSignedCertificate`, `New-FileCatalog`, `Set-AuthenticodeSignature`.
- There is no Inf2Cat (that comes with the WDK), and none is needed.
- So option 3b needs no download.

### 1.5 Microsoft's generic WinUSB model [S:local, `C:\Windows\INF\winusb.inf`]

- `Class = USBDevice`.
- Model `"WinUsb Device"`, matching `USB\MS_COMP_WINUSB`. That ID never matches the KeyLab, so this model is reachable only by an explicit pick.

### 1.6 A trap in our own code [S:local, `arsenal/keylab/winmidi.py` lines 76-89]

- `_match` prefers a port whose name contains "daw". If none does, it falls back to the first port containing "keylab".
- Under Windows' classic names ("KeyLab 88 mk3", "MIDIOUT2 (KeyLab 88 mk3)"), LED and screen SysEx would silently go to the MIDI cable [I].

---

## 2. Design principles

1. **Windows holds the truth.** The position is whatever driver sits on the KeyLab's parent node, plus its MIDI child in position 2. The tool reads that live every time. Receipts are history, not state.
2. **Arturia is home, and the switches form a star.**
   - Allowed moves: 1↔2 and 1↔3. A move from 2 to 3 goes through 1.
   - Every failure returns to 1.
   - Think of Gigabyte's DualBIOS on Daniel's AORUS board: one image always boots, and a failed flash falls back to it.
3. **One primitive.** `DiInstallDevice` acts on a single device instance.
   - With a named driver it goes to that position.
   - With no driver named it goes home by rank [S: Learn, fetched].
   - This is what Device Manager's "Let me pick" amounts to [I], and Arturia's installer uses the same API family [S:local].
4. **The rank guardrail.** Before every switch the tool checks that Arturia's package is "Best Ranked" for the KeyLab (`pnputil /enum-devices /instanceid … /drivers`). If it isn't, the tool refuses: home would not be safe.
5. **No kernel code of ours in any position.**
   - Positions 1 and 2 run attested or in-box drivers [S:local].
   - Position 3 runs Microsoft's `winusb.sys`, a framework (KMDF) driver signed "Microsoft Windows" [S:local].
   - So Secure Boot, test mode and memory integrity never come into it [S: L6/L7 via the curriculum].

---

## 3. The three positions at a glance

| | **1. Arturia (home)** | **2. Microsoft class driver** | **3. WinUSB plus our program** |
|---|---|---|---|
| **KeyLab parent node** | `arturiausbmidi`, stack `arturiausbmidi \| ACPI \| USBHUB3`; oem22 = arturiausbmidi.inf [S:local] | `usbccgp`, stack `usbccgp \| ACPI \| USBHUB3`; usb.inf "USB Composite Device" | `WinUsb`, stack `WinUsb \| ACPI \| USBHUB3` [I] |
| **Children** | `TUSBAUDIO_ENUM…&KS` (ksthunk \| arturiausbmidiks \| arturiausbmidi); midisrv's KSA endpoint; 4 WinMM nodes [S:local] | `…&MI_00` audio function with usbaudio (predicted) or USBMidi2-ACX (by pick); possibly a driverless `MI_0x` for a firmware-update interface; a new midisrv endpoint [I] | None. Our program publishes a Virtual Device in Windows MIDI Services [I] |
| **Device Manager shows** | "Arturia USB MIDI Devices" → KeyLab 88 mk3, plus Sound, video and game controllers → KeyLab 88 mk3 [S:local] | Universal Serial Bus controllers → USB Composite Device; Sound, video and game controllers → KeyLab 88 mk3 ("USB Audio Device" or "USBMidi2-ACX" as its driver) [S: M1; I] | Universal Serial Bus devices → "WinUsb Device" (3a) or "KeyLab 88 mk3 (WinUSB)" (3b) [S: Learn; I] |
| **Packages needed** | oem22 + oem11, in the store [S:local] | usb.inf + wdma_usb.inf or usbmidi2.inf, in-box [S:local] | winusb.inf, in-box; 3b adds our INF + catalog |
| **Firmware updates** | Yes: MCC uses `TUSBAUDIO_StartDfuDownload` [S:local strings] | No: go home first [I] | No: go home first [I] |
| **Who writes to the USB pipes** | Thesycon's driver | usbaudio or USBMidi2 | Our process, with timeouts and recovery [S: WinUSB pipe policy] |

Nothing is ever deleted to switch: every package stays in the store. "Toggle" means re-binding, never uninstalling. Deleting Arturia's package to "turn it off" would leave home unreachable without running a vendor installer, and would remove the safety net for the updater identity (§1.2).

---

## 4. Position 2: which Microsoft driver, and how Microsoft says to move it

**The default should be usbaudio ("2-classic"). USBMidi2-ACX ("2-new") is an explicit sub-choice.**

**Why Windows picks usbaudio by itself [I]:**
- Once the parent is on usbccgp, Windows groups the audio-class interfaces into one child. That child takes its IDs from the first interface, AudioControl [S: Learn interface collections, via the walk].
- `wdma_usb.inf` names `USB\CLASS_01` as a hardware ID, rank about `00FF2005`.
- `usbmidi2.inf` reaches it only through a compatible ID, rank about `00FF3105`.
- Local precedent: a class-compliant USB-MIDI device (VID 552D) bound to usbaudio here [S:local, the walk].
- Microsoft: "most MIDI 1.0 devices remain on existing drivers by default" [S, via the driver study].

**Why usbaudio is the better default for experiments [I]:**
- It keeps midisrv on the same kernel-streaming transport (KSA) that Arturia's driver uses.
- So comparing positions 1 and 2 changes only the kernel driver, not the service path. That is the cleaner A/B for the hang question.

**Why 2-new is still worth a visit:**
- USBMidi2 is Microsoft's future direction, its source is open under the MIT licence, and it is a KMDF/ACX driver: chapter 7 of the course running live.
- **Caveat:** it puts the device to sleep after 15 idle minutes [S: driver study, `Device.cpp` lines 452-459]. That adds a power variable.

**How Microsoft says to move a device between them** [S: M1, fetched]:
- **Troubleshooter:** "The MIDI Troubleshooting and Repair app … gives you a button to switch it to the other one." It ships in the Tools download, which is not installed here [S: driver study].
- **Device Manager:**
  1. Find the device under Sound, video and game controllers.
  2. Update Driver → "Browse my computer for drivers".
  3. "Let me pick from a list of available drivers on my computer".
  4. Choose "USB Audio Device" or "USBMidi2-ACX".
  5. "When it's done, unplug the device, restart your PC, and plug the device back in."
- **Preparation:** "close your DAW and any other app that's using MIDI."
- **Warnings:**
  - "There's a Plug and Play bug in Windows right now that can put the old driver back after an update."
  - Devices without serial numbers lose the choice when moved to another port. The KeyLab has a serial number, so its choice follows it [S:local].
  - "If a device needs a driver from its manufacturer, neither of these two drivers will work for it."
- **The KeyLab needs one step first,** because Arturia's driver holds the whole device: pick "USB Composite Device" on the parent. M1's steps then apply to the child [S: driver study §4; I].

---

## 5. Position 3: which node, what INF, what signing, and what our program does

### 5.1 Which node gets WinUSB

**Primary: the whole device**, the parent `USB\VID_1C75&PID_02CE\7656400341020110` [I].
- This is the same node Arturia's driver holds, so 1↔3 is a single-node swap.
- No usbccgp layer is involved.
- Our program opens interface 0 with `WinUsb_Initialize` and reaches the MIDIStreaming interface with `WinUsb_GetAssociatedInterface` [S: L12; I that this works on this device].

**Fallback:** parent on usbccgp (as in position 2), with WinUSB only on the `MI_00` audio function. Microsoft recommends this pattern for composite devices [S: driver study citing Learn supported-usb-classes]. Use it if the whole-device bind fails its first liveness check.

### 5.2 Binding and signing: the options

| Route | Signed by | Trust change | Switching effort | Verdict |
|---|---|---|---|---|
| **3a.** Device Manager: Let me pick → Universal Serial Bus devices → "WinUsb Device" [S: Learn winusb-installation, fetched] | Microsoft (in-box) | None | A manual pick each time. Then add a `DeviceInterfaceGUIDs` value under Device Parameters and reconnect [S: same page] | **Recommended first.** It is also the driver study's choice |
| **3b.** Our own INF + catalog, signed with a throwaway certificate (libwdi's method, done by us) | A self-made certificate, installed to Trusted Root and Trusted Publisher | Yes: a machine root certificate | One command (`DiInstallDevice` with our package) | **Daniel's call**, and only if position 3 becomes a daily position |
| Zadig/libwdi itself | Same as 3b, but its own tooling [S: libwdi FAQ] | Yes | One click, but it builds its own INF, whose rank we don't control [I] | Avoid: our INF's rank guardrail matters |
| A purchased code-signing certificate | A commercial certificate authority | None (already trusted) | One command | Costs money every year; overkill [I] |
| Attestation through Partner Center | Microsoft | None | One command | Needs an EV certificate and a company; overkill [S: L6] |
| Microsoft OS descriptors in the device firmware | — | — | Automatic | Not ours to add. `osvc = 00 00` on every revision [S:local] |
| An unsigned INF | — | — | — | Refused: a package must be signed to be staged [S: PnP signing requirements, fetched]. The common Windows 10/11 symptom is "The third-party INF does not contain digital signature information" [I] |

**Two different checks, which is the course lesson in this table** (chapter 6):
- **Staging (Plug and Play).** The package catalog must be signed, by WHQL or a test certificate in development [S: PnP signing requirements, fetched]. Microsoft's WinUSB page says a signed catalog "is required to install WinUSB on Windows" [S: fetched].
- **Kernel load (code integrity).** The kernel binary itself must carry Microsoft's signature.
- Position 3b passes the second check for free, because its only kernel binary is Microsoft's `winusb.sys`.

**What 3b's certificate would mean** [S: libwdi FAQ, fetched]:
- libwdi installs its certificate into "Root (Trusted Root Certification Authorities)" and "Trusted Publisher".
- The private key "is generated at runtime, on the end user machine" and "is destroyed after driver package signing completes", so "nobody … [has] the ability to reuse these certificates".
- Our version would do the same:
  - limit the certificate to code signing;
  - give it a long validity, since there is no timestamp;
  - record its thumbprint in the receipt;
  - delete it later with `certutil -delstore Root <thumbprint>` and `certutil -delstore TrustedPublisher <thumbprint>` [I].

### 5.3 The 3b INF (sketch, adapted from Microsoft's template [S: Learn, fetched]; not built or installed)

```
; keylab_winusb.inf -- position 3b (design sketch)
[Version]
Signature   = "$Windows NT$"
Class       = USBDevice
ClassGUID   = {88BAE032-5A81-49f0-BC3D-A4FF138216D6}
Provider    = %Mfg%
CatalogFile = keylab_winusb.cat
DriverVer   = 01/01/2000,0.0.0.1     ; old on purpose: loses every tie
PnpLockdown = 1

[Manufacturer]
%Mfg% = Aurora,NTamd64

[Aurora.NTamd64]
; hardware-ID slot left EMPTY, the KeyLab's ID in the compatible slot:
; Windows scores this 0x1001, one rung below Arturia's 0x0001, so it is
; never chosen automatically (not on replug, not for the REV 0500 updater
; identity), only by an explicit pick.
%Desc% = KeyLab_WinUsb, , USB\VID_1C75&PID_02CE

[KeyLab_WinUsb]
Include = winusb.inf
Needs   = WINUSB.NT
[KeyLab_WinUsb.Services]
Include = winusb.inf
Needs   = WINUSB.NT.Services
[KeyLab_WinUsb.HW]
AddReg  = KeyLab_AddReg
[KeyLab_AddReg]
HKR,,DeviceInterfaceGUIDs,0x10000,"{<one fixed GUID of ours>}"

[Strings]
Mfg  = "Akashic Aurora (local)"
Desc = "KeyLab 88 mk3 (WinUSB, Aurora)"
```

**Why the empty hardware-ID slot works:**
- The rule: a device hardware ID that matches an INF *compatible* ID scores 0x1000 to 0x1FFF [S: L1, via the walk; I for applying it here].
- The syntax: the empty first slot is the same form `c_swdevice.inf` uses (`SoftwareDevice,,SWD\GenericRaw`) [S:local].
- Arturia's INF writes `InterfaceGUID`, a different value name from WinUSB's `DeviceInterfaceGUIDs`, so the two never collide [S:local; S: Learn].

**One-time setup [I]:**
1. Write a `.cdf` naming the INF, and build the catalog with `makecat`.
2. Create a non-exportable code-signing certificate with `New-SelfSignedCertificate`.
3. Sign the catalog with `signtool sign /fd sha256`.
4. Import the public certificate into LocalMachine Root and TrustedPublisher.
5. Delete the private key.
6. Stage the package with `pnputil /add-driver keylab_winusb.inf`, **without `/install`**.
7. Verify: `pnputil /enum-devices /instanceid … /drivers` must list ours as "Outranked", rank about `00FF1001`. If it says "Best Ranked", delete it at once with `pnputil /delete-driver oemNN.inf`.

### 5.4 What our program does in position 3

This is the hub from the driver study (§2.4-2.5), with its bottom layer swapped to WinUSB pipes. Except where marked, these are design choices [I].

- **Opening the device:**
  - Open it by our interface GUID: `SetupDiGetClassDevs`, then `CreateFile` (overlapped), then `WinUsb_Initialize`.
  - In 3a, until the GUID value exists, open through the hub's generic USB-device interface `{A5DCBF10…}` instead, which is present on the node today [S:local; I that WinUSB accepts it].
- **Finding the pipes:** find the MIDIStreaming interface (class 01, subclass 03) and its bulk IN and OUT pipes.
- **OUT (to the keyboard):**
  - one transfer in flight, no longer than the packet size;
  - `PIPE_TRANSFER_TIMEOUT` of 1000 ms [S: L12];
  - on timeout: abort, then reset the pipe, then probe [S: driver study].
- **IN (from the keyboard):** 2 to 4 reads always posted, with `RAW_IO` and `AUTO_CLEAR_STALL` [S: L12].
- **The USB-MIDI codec:** packing and unpacking the 4-byte event packets, with SysEx reassembled per cable.
- **Queues and pacing:**
  - one queue per cable, so the DAW cable can't block the keys;
  - the governor (12 SysEx per 100 ms; screen frames at least 60 ms apart);
  - a Device Inquiry heartbeat.
- **Recovery ladder:** abort/reset, then reopen, then port cycle (admin) [S: Learn, via the driver study], then a human replug.
- **Plumbing:** unplug and replug notifications, counters for the dashboard, and a supervisor that restarts the program.
- **Power:** WinUSB never puts the device to sleep unless `DeviceIdleEnabled` is set [S: driver study].

### 5.5 How FL gets ports in position 3

**Primary: a Windows MIDI Services Virtual Device named like the real ports, "KeyLab 88 mk3 MIDI" and "KeyLab 88 mk3 DAW".**
- Only apps built on the SDK can create one, WinMM apps can use it, and "When the application closes, the endpoint closes" [S: Virtual Device KB, fetched].
- Our program runs only in position 3, so the names never collide with Arturia's ports. FL's saved settings and Arturia's FL script, which matches on the Device Inquiry reply, keep working, as long as our program passes the inquiry and reply through untouched [S: guide on FL's inquiry; I].
- **Caveat:** "challenges around port numbers with dynamically-created endpoints" [S: KB].

**Alternative: loopback pairs.** These persist on their own [S: KB]. They need different names (for example "… (Aurora)"), or they would collide with the real ports in position 1 [I].

**Both routes need the Windows MIDI Services Tools/SDK runtime**, which is not installed here [S: driver study]. It is an approval item (§11).

---

## 6. The switch, step by step

### 6.1 The tool (design only)

The verb would be `py -m arsenal.keylab driver …`, a Python ctypes helper over `setupapi.dll`, `newdev.dll` and `cfgmgr32.dll`. It must run as 64-bit Python, because the calls fail with `ERROR_IN_WOW64` from 32-bit [S: Learn].

| Command | What it does |
|---|---|
| `driver status` | Read-only; no admin, no MIDI sent. Prints the current position read live from Windows, the stacks, the port names, the scoreboard and "firmware updates: OK here / go home first". `--live` adds a Device Inquiry |
| `driver go class` / `driver go class-new` / `driver go winusb` | Switch away from home. Admin only; never self-elevates; refuses unless the KeyLab is at home |
| `driver home` | `DiInstallDevice(parent, no driver)`, so Windows picks by rank |
| `--dry-run` | Prints the driver it would select, and calls nothing |

**How the helper picks a driver [I]:**
- It opens the device with `SetupDiOpenDeviceInfoW(instance ID)` and builds its compatible-driver list with `SetupDiBuildDriverInfoList(SPDIT_COMPATDRIVER)`.
- It chooses an entry by its original INF name (`arturiausbmidi.inf`, `usb.inf`, `wdma_usb.inf`, `usbmidi2.inf`, `keylab_winusb.inf`), its provider and its matched ID, read with `SetupDiGetDriverInfoDetailW`.
- It then calls `DiInstallDevice(NULL, set, device, &driver, DIIDFLAG_NOFINISHINSTALLUI, &needReboot)` [S: Learn, fetched].
- Then `CM_WaitNoPendingInstallEvents(30 s)` [S: cfgmgr32 docs, not fetched], then the checks.

### 6.2 Each switch: the mechanism and its manual fallback

| Switch | Tool action | Manual fallback (Device Manager) |
|---|---|---|
| **1 → 2-classic** | `DiInstallDevice(parent, usb.inf "USB Composite Device")`. The MI_00 child then installs by itself (predicted usbaudio) | View → Devices by type → "Arturia USB MIDI Devices" → KeyLab 88 mk3 → Update driver → Browse my computer → Let me pick → "USB Composite Device" → Next |
| **2-classic → 2-new** | `DiInstallDevice(MI_00 child, usbmidi2.inf "USBMidi2-ACX")` | Sound, video and game controllers → KeyLab 88 mk3 → Update driver → … → "USBMidi2-ACX" [S: M1] |
| **2 → 1 (home)** | `DiInstallDevice(parent, NULL)`, best rank = Arturia's oem22 [S: Learn; S:local rank]. Arturia's KS child returns through its own oem11 | Universal Serial Bus controllers → the "USB Composite Device" whose Details show `VID_1C75&PID_02CE` → Update driver → … → "KeyLab 88 mk3" |
| **1 → 3a** | Guided: the tool runs preflight, then pauses with the steps; Daniel picks; the tool writes `DeviceInterfaceGUIDs`, runs `pnputil /restart-device` and the liveness checks [I] | Update driver → Browse → Let me pick → untick "Show compatible hardware" if needed → Universal Serial Bus devices → "WinUsb Device" → accept the compatibility warning [S: Learn] |
| **1 → 3b** | `DiInstallDevice(parent, keylab_winusb.inf)`; the package was staged once, without `/install` | Update driver → Let me pick → "KeyLab 88 mk3 (WinUSB, Aurora)" |
| **3 → 1 (home)** | Stop our program (it holds the handle), `DiInstallDevice(parent, NULL)`, delete `DeviceInterfaceGUIDs` | As 2 → 1, starting from Universal Serial Bus devices |
| **Last-resort home** | `pnputil /remove-device <id>`, then `pnputil /scan-devices`. The device is re-detected and Windows picks by rank = Arturia [S:local verbs; I] | Uninstall device (leave "delete the driver" **unticked**) → Action → Scan for hardware changes |

**Where the other commands fit:**
- `pnputil /add-driver` (no `/install`): stages our 3b package once.
- `pnputil /delete-driver oemNN.inf /uninstall`: retires our 3b package only. It is never run on Arturia's or Microsoft's packages.
- `DiInstallDriver`: what Arturia's installer uses (stage, then install if better) [S:local]. It is not a toggle.

### 6.3 Preconditions the tool checks (it refuses if any fails)

1. It is running elevated (`DiInstallDevice` needs admin: `ERROR_ACCESS_DENIED` otherwise [S: Learn]).
2. The KeyLab is present, started, with no problem code. The instance with serial `7656400341020110` is located through its parent chain.
3. The current position is known and the move is allowed (star topology: no 2 ↔ 3 directly).
4. Home is safe: Arturia's `arturiausbmidi.inf` is "Best Ranked" for the parent, and any package of ours is "Outranked".
5. The target package is in the store, found by original name.
6. These programs are not running: `FL64.exe`, `Analog Lab V.exe`, `MIDI Control Center.exe`, `Arturia Software Center.exe`, `ArturiaSoftwareCenterAgent.exe` (paths from §1.3/§1.4 [S:local]), and in position 3, our own hub.
7. No `python` or `py` process has `arsenal.keylab` on its command line. One is running right now [S:local].
8. No reboot is pending (the Session Manager `PendingFileRenameOperations` value, and no device in "needs restart").
9. Liveness before the switch passes. A KeyLab that is already hung is not switched: run the hang ladder instead, or the driver gets blamed for a firmware fault.
10. For 3b: the one-time setup receipt (certificate thumbprint, staged package) exists.

### 6.4 What it prints (illustration; `<…>` are placeholders, not measurements)

```
KeyLab driver toggle: position 1 (Arturia) -> position 2 (Microsoft class driver)
Preflight
  ok   running as Administrator
  ok   KeyLab 88 mk3, serial 7656400341020110, port 8, started
  ok   now: arturiausbmidi (arturiausbmidi.inf = oem<NN>.inf, Arturia 1.7.0.0)
  ok   home safe: Arturia Best Ranked 00FF0001
  ok   target in store: usb.inf "USB Composite Device" 00FF2006
  ok   closed: FL, Analog Lab, MIDI Control Center, Arturia Software Center + Agent
  ok   no arsenal.keylab process; no reboot pending
  ok   before: Device Inquiry answered on "KeyLab 88 mk3 DAW" in <n> ms (firmware <v>)
Switch
  ..   DiInstallDevice(parent, usb.inf)            <n> s   reboot needed: no
  ..   Windows finishing child installs           <n> s
  ok   parent stack: usbccgp | ACPI | USBHUB3
  ok   child <MI_00 id>: <usbaudio|USBMidi2>, rank <rank>
  note child <MI_0x id>: no driver, class <FE/01?> (expected for an update interface)
Liveness after
  ok   ports in: <names>   out: <names>   (CHANGED from position 1: see receipt)
  ok   Device Inquiry answered on <port> in <n> ms
Result: position 2. Receipt: state\arsenal\keylab\receipts\driver-1to2-<stamp>.json
Firmware updates: not here. Run `driver home` first.
```

On a failure it prints the failing line, then `Rolling back to position 1 (Arturia) …`, the home liveness result, `Result: ROLLED BACK` and the receipt path.

### 6.5 The liveness check after the switch

**Where a MIDI driver is bound (positions 1 and 2):**
- Use the guide's check [S: G2 §2.2]: send one Device Inquiry `F0 7E 7F 06 01 F7` and listen on every KeyLab input for 1.5 s. Accept a reply starting `F0 7E xx 06 02 00 20 6B`, and record the four firmware-version bytes.
- Ask on the DAW port. In position 2, if no name contains "DAW", ask on each KeyLab output in turn, as the hang study did [S: hang study].
- The send runs in a worker thread with a 2 s deadline, because `midiOutLongMsg` blocks [S: G2].
- No LED or screen bursts.

**Where WinUSB is bound (position 3):**
1. `WinUsb_Initialize` succeeds.
2. `WinUsb_GetDescriptor(DEVICE)` returns 18 bytes with idVendor `0x1C75`, idProduct `0x02CE`, and bcdDevice equal to the REV value (`0x1500` today).
3. `WinUsb_GetDescriptor(CONFIGURATION)` is parsed into interfaces and endpoints.
4. `WinUsb_QueryDeviceInformation(DEVICE_SPEED)` gives the bus speed.
5. Optional end-to-end check: the inquiry as raw packets on the DAW cable, `14 F0 7E 7F | 17 06 01 F7`, with a 1000 ms OUT timeout, then reassemble the reply from IN.

[S: L12; S: driver study wire lane; I for the sequence]

**Bonus:** the first entry into position 3 is the KeyLab descriptor read that every lane has been waiting for.

### 6.6 Receipts

The tool writes one JSON file per switch to `state/arsenal/keylab/receipts/driver-<from>to<to>-YYYYMMDD-HHMMSS.json`, where the house already keeps its KeyLab receipts [S:local README]. It is marked class **eyes** when Daniel watched. Fields:

- time, operator, from and to;
- preflight results;
- before and after snapshots:
  - the parent's and child's service, INF (original name and oemNN), version, date, rank and stack;
  - the WinMM in and out names;
  - the midisrv endpoint ID;
  - the device-parameter values;
- the call made: the driver chosen, `needReboot`, `GetLastError`, duration;
- the setupapi.dev.log sections for this switch, including any veto lines [I];
- the liveness result: reply hex and latency, or the descriptor dump;
- the verdict: committed, rolled back or stuck;
- the rollback record, if there was one.

`status` keeps a pointer to the last intended position so it can flag drift, for example: "Windows put you back in position 1 at <time>". That direction is the safe one [S: M1 PnP bug; S:local 06-11 installer].

### 6.7 Automatic rollback to Arturia

**Triggers** (any one):
- `DiInstallDevice` returns FALSE;
- `needReboot` is TRUE, meaning something refused to let go [S: Learn UpdateDriver remarks on query-remove and `DI_NEEDREBOOT`];
- Windows' installs are still pending after 30 s;
- the wrong driver is bound, or a problem code appears;
- the liveness check fails.

**Action:**
1. `DiInstallDevice(parent, NULL)`, which installs Arturia by rank.
2. Delete any `DeviceInterfaceGUIDs` value we added.
3. Run the position-1 liveness check.
4. Write the receipt.

**If the triggering call reported a needed reboot:** the old driver never stopped running, so selecting Arturia again leaves the PC consistent. The tool still says a reboot is the clean finish [I].

**If home's own liveness fails, the tool prints the human ladder:**
1. Replug the KeyLab.
2. Device Manager → Let me pick → "KeyLab 88 mk3".
3. Uninstall device (driver kept) → Scan for hardware changes.
4. Reboot.
5. Last resort: Daniel runs `C:\Program Files (x86)\Arturia\MIDI Control Center\ArturiaMIDI_DriverSetup.exe`, already on disk [S:local]. It is a vendor binary, so he runs it himself.

**Drill doctrine:** a `--inject-liveness-failure` flag forces a rollback, so the rollback path gets its own dated receipt before it is trusted.

---

## 7. What each program sees, in each position

| | **1. Arturia** | **2. Microsoft class** | **3. WinUSB + ours** |
|---|---|---|---|
| **FL Studio** | In: "KeyLab 88 mk3 MIDI", "…DAW"; out: the same [S:local]. Arturia's script binds by Device Inquiry [S: guide] | KeyLab ports named by Windows MIDI Services' rules: by default "Windows decides per endpoint": classic "MIDIOUT2 (Some Device)" or the device's own iJack names [S: naming KB, fetched]. If the names differ, FL's port setup and the script need redoing; that happened to users on usbaudio [S: Image-Line forum, via the driver study]. Back in position 1 the old names should return [I] | Only our ports, present only while our program runs [S: Virtual Device KB]. Named like position 1, so FL's settings carry over [I] |
| **Analog Lab V** | Works. It needs the exact Windows port names for its screen and buttons [S: forum t/5294]. It links Thesycon's API [S: driver study] | Notes through the ports. Screen integration depends on the names [I]. Its Thesycon API calls find no driver; it carries a "Could not find the driver .dll" message [S: driver study; I] | Through our ports. Screen integration depends on names and on SysEx passing through untouched [I] |
| **MIDI Control Center** | Sees the device. Firmware updates through Thesycon's firmware-update calls [S: driver study strings] | Likely no device and no update [I]. The experiment can check this (optional, Daniel's call) | No device [I] |
| **House tools** (`arsenal.keylab`) | As today | If no name holds "DAW", `_match` falls back to the MIDI cable [S:local code]. Use an explicit `--port`, or keep them stopped | They talk to our program (the hub) |
| **midisrv endpoint** | `MIDIU_KSA_16201702556534547415` [S:local] | A new endpoint ID: KSA for usbaudio; probably the plain KS transport for USBMidi2 [I] | Our Virtual Device |

---

## 8. Risks

| Risk | Effect | Mitigation |
|---|---|---|
| A process holds the device during a switch | Windows can't stop the old driver, so the switch needs a reboot [S: Learn remarks] | Preflight process checks; a needed reboot counts as failure and sends the KeyLab home; the receipt names who refused (from setupapi.dev.log) [I] |
| Half-switched state (parent moved, child failed) | No MIDI | Settle wait, child checks, automatic home |
| A firmware update in the wrong position, or a switch during an update | MCC likely won't find the device (harmless); switching mid-update could leave the unit in its updater [I] | Updates only in position 1; preflight refuses while MCC runs; `status` says "go home first" |
| Port names change in position 2 | FL's settings and Arturia's script mis-bind; our tools send SysEx to the wrong cable [S:local code; S: forum] | The receipt records the names; explicit `--port`; the experiment measures it |
| Windows reverts the choice (the PnP bug, Windows Update, Arturia's installer) | The KeyLab is back on Arturia's driver | That is the safe direction; `status` flags the drift [S: M1; S:local 06-11] |
| Our package outranks Arturia's (a wrong INF) | Windows would choose ours by itself, including for the updater identity, and firmware updates would break | The empty hardware-ID slot plus an old date; checked "Outranked" after staging, or deleted at once |
| USBMidi2's 15-minute idle sleep | A power variable in the A/B; a possible delay on the first note after idle [I] | Use usbaudio for A/B work; note it in receipts |
| The 3b root certificate | A machine-wide trust change | Key destroyed after one signature; code-signing only; thumbprint recorded; removal steps written down; Daniel's call |
| Our program dies in position 3 | The keyboard goes silent in FL | Supervisor; `driver home` always works |
| Arturia's package deleted by mistake | Home is gone | The tool never deletes anything but our own package; the vendor installer is on disk as a last resort |
| Old device entries cleaned up (Storage Sense deleted a KeyLab entry on 01-28 [S:local]) | A remembered usbmidi2 pick on MI_00 can vanish [I] | The tool checks the child on every visit |
| A needed reboot | After a reboot the house's Aurora tasks must be started by hand (house note) | Run switches when a reboot is acceptable |

---

## 9. The first experiment: 1 → 2 → 1, by hand, with Daniel present

**Shape:** about 40 minutes, Device Manager plus read-only looks. No code is built and nothing is downloaded. It fits one Forest Walk: predict before looking, then a teach-back.

### Stage 0: prepare (10 min)

1. Close FL. Quit Analog Lab, MIDI Control Center, Arturia Software Center **and its tray Agent**, and any `arsenal.keylab` process (`vj --no-leds` was running tonight).
2. Open Terminal (Admin), to be used for looking only. Save:
   - `pnputil /enum-devicetree "USB\VID_1C75&PID_02CE\7656400341020110" /stack /drivers` as `before.txt`;
   - `pnputil /enum-devices /instanceid "USB\VID_1C75&PID_02CE\7656400341020110" /drivers`;
   - `py -m arsenal.keylab ports`.
3. Liveness: the guide's Device Inquiry check, or `py -m arsenal.keylab monitor` with a pad press.
4. **Write down the predictions:**
   - **P1.** Which driver will Windows put on the MIDI part: usbaudio (the walk) or USBMidi2 (the course)?
   - **P2.** How many `MI_xx` children appear, and with which interface classes?
   - **P3.** Will the switch need a reboot? (The 06-11 precedent says no.)
   - **P4.** What will the port names be?
   - **P5.** Will the KeyLab answer the inquiry on Microsoft's driver?
   - **P6.** After returning home, will the names and the endpoint ID be identical?

### Stage 1: go to position 2 (10 min)

1. Device Manager: "Arturia USB MIDI Devices" → KeyLab 88 mk3 → Update driver → Browse → Let me pick → "USB Composite Device" → Next.
2. **Look:**
   - the device tree with stacks, saved as `pos2.txt`;
   - the child's own scoreboard: `pnputil /enum-devices /instanceid "<MI_00 id>" /drivers` (this answers P1);
   - each `MI_xx` child's compatible IDs: class 01 means audio or MIDI, FE/01 means a firmware-update interface [S: USB DFU class, standard reference; I] (this answers P2 without a descriptor tool);
   - the new "Select Drivers" block at the end of `C:\Windows\INF\setupapi.dev.log`: the same scoreboard the 06-11 log printed.
3. **Liveness:**
   - the inquiry on each KeyLab output, with both inputs listened to;
   - a key and a pad press into `monitor --port "<new name>"`.
4. **Stop rule:** no reply → one unplug and replug (Microsoft's own step) → still nothing → Stage 2 now.
5. **Optional, Daniel's call:**
   - (a) Open MCC only to see whether it finds the KeyLab. Never click update.
   - (b) MI_00 → USBMidi2-ACX by hand. I'd defer this to a second walk, to keep one variable per session.

### Stage 2: go home (5 min)

1. Device Manager: Universal Serial Bus controllers → the KeyLab's "USB Composite Device" (Details → Hardware Ids shows `VID_1C75&PID_02CE`) → Update driver → Let me pick → "KeyLab 88 mk3" → Next.
2. **Look:** compare the new tree with `before.txt`, check `ports` (names identical?), check the midisrv endpoint ID (identical?), and run the inquiry.
3. Restart the house's KeyLab services. Open FL: does its saved KeyLab setup work untouched?
4. **If home fails:** replug → pick Arturia again → Uninstall device (driver kept) + Scan for hardware changes → reboot → Arturia's installer, which Daniel runs.

### Stage 3: receipt and teach-back (10 min)

- Write a dated eyes-class receipt by hand. The same fields the tool will write later.
- The teach-back prompts are in §10.

---

## 10. What the experiment teaches

**Chapter 5, how Windows picks a driver.**
- Daniel watches the scoreboard decide twice:
  - in position 2, the child's driver is chosen by rank (P1 settles the course-versus-walk disagreement with Windows' own numbers);
  - going home, Windows' rank picks Arturia's driver from Device Manager's list again.
- The setupapi log prints "Selected", "Outranked" and the rank values in plain text.
- **Teach-back:** "Why did going home need no download and no choice?"

**Chapter 3, device stacks.**
- In each position only the top of the parent's stack changes (arturiausbmidi → usbccgp → back), while `ACPI | USBHUB3` stay put.
- usbccgp then acts as a bus driver and invents `MI_xx` children, exactly as Thesycon invents `TUSBAUDIO_ENUM…&KS`.
- **Teach-back:** "Which driver created each node's bottom layer?"

**Chapter 8, USB descriptors.** The `MI_xx` compatible IDs are the KeyLab's interface descriptors, printed by Windows itself.

**Chapter 10, the MIDI stack, and the machine walk's layers 5 to 8.**
- midisrv tears down and rebuilds the endpoint and the WinMM nodes.
- The naming rules show up live.
- midisrv keeps running throughout, which is chapter 2's fenced yard.

**Chapter 2, plus the query-remove handshake.**
- **Teach-back:** "Why did FL have to be closed?" Windows asks every program holding the device to let go before it swaps the function driver. A program that refuses forces a reboot.

**Chapter 6, signing.** Every driver touched is in-box or attested: no trust change. That is the contrast for position 3b later.

**Chapter 11.** Position 3 is the same mechanics with WinUSB on top. Daniel will recognise every line of the tool's output, because the tool automates what he did by hand.

**Build order after the experiment [I]:**
1. `driver status` (read-only).
2. Switching 1↔2 with the helper, plus the rollback drill.
3. 3a binding plus the WinUSB descriptor liveness check, alongside the hub's WinUSB layer (driver study stage 4).
4. 3b, only if Daniel wants it.

---

## 11. Needs Daniel's approval (nothing done)

| # | What | Source, size | Notes |
|---|---|---|---|
| 1 | The 1 → 2 → 1 experiment (driver switches are system changes) | In-box; nothing to download | Admin; FL and Arturia's apps closed |
| 2 | Optional: open MCC in position 2 to see whether it finds the KeyLab | On disk | Vendor binary, Daniel runs it; never press update |
| 3 | Windows MIDI Services Tools/SDK runtime (needed for position 3's ports, and the troubleshooter's switch button) | github.com/microsoft/MIDI releases, tag inbox-preview-12, 223,376,824 bytes [S: driver study] | Preview release; installs the Windows App SDK runtime |
| 4 | Optional: a .NET SDK for a C# Virtual Device helper, if Python can't reach the SDK | Size not checked | Only if needed [I] |
| 5 | Position 3a binding | In-box winusb.inf | Adds a `DeviceInterfaceGUIDs` value under Device Parameters |
| 6 | Position 3b: a root certificate plus our package | Tools on disk (makecat, signtool, New-SelfSignedCertificate) [S:local] | A trust-store change. Not before 3a has been lived with |

No WDK is needed. No Zadig.

---

## 12. Open questions, each answered by a step above

- **Which driver Windows puts on the MIDI part, and how many interfaces the KeyLab has.** Experiment Stage 1.
- **Whether a switch completes without a reboot while midisrv runs.** The 06-11 precedent says yes, but whether any app had MIDI open then is unknown. Experiment, P3.
- **Port names under Microsoft's driver, and whether FL's setup survives the round trip.** Stages 1 and 2.
- **Whether MCC needs Arturia's driver to see the device at all.** Optional probe 2.
- **Whether the REV 0500 updater identity keeps the serial number.** Run `driver status` before and after the next firmware update.
- **Whether WinUSB on the whole device exposes the MIDIStreaming pipes.** The first 3a visit; the fallback is WinUSB on MI_00.

---

## Sources

**Fetched tonight:**
- M1, Windows MIDI Services KB, "How to switch between MIDI class drivers": https://microsoft.github.io/MIDI/kb/how-to-switch-between-class-drivers/
- MIDI 1.0 port naming KB: https://microsoft.github.io/MIDI/kb/midi1-name-mapping/
- Virtual Device App KB: https://microsoft.github.io/MIDI/kb/virtual-device-app/
- DiInstallDevice: https://learn.microsoft.com/en-us/windows/win32/api/newdev/nf-newdev-diinstalldevice
- UpdateDriverForPlugAndPlayDevicesW: https://learn.microsoft.com/en-us/windows/win32/api/newdev/nf-newdev-updatedriverforplugandplaydevicesw
- WinUSB installation for developers: https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/winusb-installation
- PnP device installation signing requirements: https://learn.microsoft.com/en-us/windows-hardware/drivers/install/pnp-device-installation-signing-requirements--windows-vista-and-later-
- libwdi FAQ: https://github.com/pbatard/libwdi/wiki/FAQ

**Cited, not fetched tonight:**
- L1/L2 rank rules and L6/L7 signing policy (via the machine walk and the curriculum).
- L12 WinUSB pipe policy.
- `CM_WaitNoPendingInstallEvents` (cfgmgr32).
- The USB DFU class code.

**Local, read-only:**
- `C:\Windows\INF\setupapi.dev.20260715_043401.log`: lines 4505-4591 and 7442-7711 (the 06-11 switch), and 49904 (an OS update re-reading Arturia's KS package).
- `C:\Windows\INF\setupapi.dev.20260214_034609.log`: line 46844 (Storage Sense deleting the serial-less KeyLab entry).
- `HKLM\SYSTEM\CurrentControlSet\Control\usbflags\1C7502CE*`: key last-write times.
- `C:\Windows\INF\winusb.inf`.
- `pnputil /?`.
- The process list.
- The Windows SDK folder: `C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\`.

**Our documents:**
- `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-driver-study-2026-10-27.md`
- `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-dev-guidance-and-hang-guide-2026-10-27.md` (G2)
- `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-hang-study-2026-10-26.md`
- `E:\AI-Setup\arsenal\keylab\winmidi.py`
- `E:\AI-Setup\arsenal\keylab\README.md` (the receipts location)

No files were written.

---

## The machine walk (verbatim)

# Machine walk: the KeyLab on Daniel's PC, from the CPU to FL Studio (2026-10-27, read-only)

The KeyLab's path on this PC has nine layers, from the Ryzen's PCIe root port up to the port names FL sees, and I re-measured every one of them tonight. Three findings matter most for the toggle question:

1. **The toggle already exists on this machine.** It is a two-entry list on the KeyLab's own device node: Arturia's driver, and Windows' "USB Composite Device".
2. **Windows' own default would probably be the old usbaudio.sys, not USBMidi2.** If we switch to Windows' drivers, Windows will most likely pick usbaudio.sys for the MIDI part, and USBMidi2 has to be picked by hand. This corrects the curriculum's Chapter 5.
3. **A driver package of our own would compete on the same scoreboard and could even win it.** For that, Windows must trust our signing certificate, and installing that trust is a security change and Daniel's call.

**Grades:** [S] a cited source says it ("fetched" means read tonight). [S:local] I measured it read-only on this PC tonight. [I] my inference.

**Before starting** I read `research/reviewed/keylab-liberation-2026-10-22/keylab-driver-study-2026-10-27.md` (it exists, 945 lines). This walk builds on it and does not repeat its binary analysis.

**What I did**, all read-only:
- Get-PnpDevice and Get-PnpDeviceProperty on the whole chain and on past devices.
- pnputil with `/enum-devices /drivers /resources`, `/enum-devicetree`, `/enum-interfaces /properties` and `/enum-drivers /class /files /devices`.
- driverquery; registry reads (services, Device Parameters, usbflags, Class, Drivers32, the Windows MIDI Services key, Secure Boot, Code Integrity); one Win32_DeviceGuard query.
- INF text from the DriverStore and C:\Windows\INF.
- File versions and Authenticode status of 15 binaries, plus a small import-table reader.
- The local Windows SDK headers.
- One WinMM capability listing (`midiInGetDevCapsW` / `midiOutGetDevCapsW`). It loads wdmaud2.drv and asks midisrv for the list, but opens no port.
- 6 web pages.

**What I did not do:** open any KeyLab MIDI port or USB handle, touch FL, run vendor code, install, switch, download or change anything, edit the repo, or leave it.

---

## What tonight's walk adds to or corrects in the course

1. **The toggle's positions, read straight off Windows** [S:local].
   - Command: `pnputil /enum-devices /instanceid "USB\VID_1C75&PID_02CE\7656400341020110" /drivers`
   - It lists exactly two matching drivers for the KeyLab:
     - **oem22.inf**: Arturia 1.7.0.0, rank `00FF0001`, "Best Ranked / Installed".
     - **usb.inf**: "USB Composite Device" (usbccgp), rank `00FF2006`, "Outranked".
   - Both are already in the driver store, so switching needs no download.
2. **Correction to Chapter 5: usbaudio, not USBMidi2, would most likely win the KeyLab's MIDI function by default.**
   - Without an Interface Association Descriptor, Windows groups a device's consecutive audio-class interfaces into one child. That child's compatible IDs "are taken... from the first USB interface descriptor in each interface collection" [S: Learn "Support for interface collections", fetched]. For a standard USB-MIDI 1.0 device that first interface is AudioControl (SubClass 01), not MIDIStreaming (03) [S: U2; I for the KeyLab, whose descriptors are unread].
   - This Windows build also puts three vendor-qualified IDs first (`USB\COMPAT_VID_xxxx&Class_01…`) [S:local, seen on several devices].
   - So the generic `USB\Class_01` sits at position 5 of the child's compatible-ID list.
   - **wdma_usb.inf (usbaudio)** names `USB\CLASS_01` as its INF hardware ID. Score: 0x2000 + 5, so rank `00FF2005`.
   - **usbmidi2.inf** names `USB\CLASS_01&SUBCLASS_03&PROT_00` as its hardware ID, which doesn't match. It reaches `USB\CLASS_01` only as its second INF compatible ID. Score: 0x3000 + 5 + 1×0x100, so rank `00FF3105` [S: L1 formula, fetched; I for the KeyLab].
   - **Local precedent** [S:local]. A class-compliant "USB Midi " device (VID 552D, PID 4348) was plugged in here on 2025-12-31 and 2026-01-01:
     - it got usbccgp on the parent and a single `MI_00` child (no `MI_01`);
     - the child's compatible IDs start `…Class_01&SubClass_01…`;
     - it was bound to usbaudio through `USB\Class_01` at rank `00FF2005`.
   - The NZXT USB MIC and the C922 webcam's audio function bind exactly the same way today [S:local].
   - **The exception** is a KeyLab whose MIDIStreaming interface is enumerated alone. Then usbmidi2 matches at position 3 (`00FF2003`) and wins [I].
   - This also matches Microsoft's line that "most MIDI 1.0 devices remain on existing drivers by default" [S: overview, cited in the driver study].
   - **So "native" is two steps:** set the parent to USB Composite Device, then, if wanted, set the child to USBMidi2-ACX by hand [S: M1, fetched; I].
3. **Our own driver package would be ranked on the same scale.**
   - A trusted third-party Authenticode signature, "even... MakeCert", gets the best signature score [S: L2, fetched]. AllSignersEqual has been on by default since Windows 7 [S: Learn "Overview of the driver package selection process", fetched].
   - An INF of ours naming `USB\VID_1C75&PID_02CE&REV_1500` would score 0x0000. That beats Arturia's 0x0001, so ours would become the automatic default.
   - Naming `USB\VID_1C75&PID_02CE` instead ties at 0x0001. Then "the most recent date" wins, then "the highest version" [S: selection overview, fetched].
   - "Trusted" means installing our own certificate into the machine's trust stores, which is Zadig's method. That is a security change and Daniel's call [S: Z1; I].
   - A side effect worth testing [I]: the REV value changes with firmware (this unit has shown 0500, 1101, 1201 and 1500). A REV-specific INF would stop matching after a firmware update, so Arturia would win again on its own, which is exactly the side we want during updates.
4. **The KeyLab hangs off the first of two chipset chips** [S:local].
   - The board is a Gigabyte X870E AORUS MASTER with a Ryzen 9 9950X3D.
   - There are two `1022:43FD` USB controllers:
     - the KeyLab's, at `PCI(0201)#PCI(0000)#PCI(0C00)#PCI(0000)`;
     - a second one behind the first chip's downstream port 08.0, at `…#PCI(0800)#PCI(0000)#PCI(0C00)#PCI(0000)`.
   - The CPU has its own controllers: 1022:15B6 and 15B7 (USB 3.10) and 15B8 (USB 2.0).
   - So the KeyLab is not on the CPU's own USB, but it is on the chipset closest to the CPU [I].
5. **The framework tally across the path** [S:local import tables]:
   - Microsoft's two bottom layers are KMDF: USBXHCI and USBHUB3 both import `WDFLDR.SYS`, and `Ucx01000` is loaded.
   - Thesycon's two top layers are classic WDM.
   - So the KeyLab's path is "framework at the bottom, hand-written at the top".
6. **The WinMM names FL sees**, measured [S:local]:

   | Direction | Index | Name |
   |---|---|---|
   | In | 0 | KeyLab 88 mk3 MIDI |
   | In | 1 | KeyLab 88 mk3 DAW |
   | Out | 0 | Microsoft GS Wavetable Synth |
   | Out | 1 | KeyLab 88 mk3 MIDI |
   | Out | 2 | KeyLab 88 mk3 DAW |

   Every port reports manufacturer 1 (Microsoft) and a "MS Vanilla driver" product ID, so Arturia's identity survives only in the name.
7. **midisrv has not restarted since 2026-10-22 03:18:55** (process 45480, 13.1 MB) [S:local].
   - The 10-26 power cycle re-created only the device nodes (23:31:45 and 23:31:47).
   - So the hang cleared without a service restart. Whatever was stuck was rebuilt when the device left and returned [S:local; S: G1; I].

---

## Chapter 0, refreshed: the tree as measured tonight

Device Manager names first; instance IDs and driver stacks follow (top of stack to bottom).

```
ACPI x64-based PC                          ROOT\ACPI_HAL\0000
 └ Microsoft ACPI-Compliant System         ACPI_HAL\PNP0C08\0
   └ PCI Express Root Complex              ACPI\PNP0A08\0
     └ PCI Express Root Port  1022:14DB    PCI 0:2.1, ACPI GPP7          stack pci | ACPI | pci
       └ PCI Express Upstream Switch Port 1022:43F4  bus 7 (UP00)         stack pci | ACPI | pci
         └ PCI Express Downstream Switch Port 1022:43F5 bus 8 dev 12 (DP60), one of 7
           └ AMD USB 3.20 eXtensible Host Controller - 1.10 (Microsoft) 1022:43FD bus 23 (XH00)
             │                                                            stack USBXHCI | ACPI | pci
             └ USB Root Hub (USB 3.0)  USB\ROOT_HUB30\7&397afaa3&0&0      stack USBHUB3 | ACPI | USBXHCI
               ├ port 7:  Generic USB Hub 1A40:0101
               ├ port 11: USB Composite Device 048D:5711 "GIGABYTE Device " (usbccgp)
               └ port 8:  KeyLab 88 mk3  USB\VID_1C75&PID_02CE\7656400341020110
                   │                                           stack arturiausbmidi | ACPI | USBHUB3   (oem22.inf)
                   └ KeyLab 88 mk3  TUSBAUDIO_ENUM\VID_1C75&PID_02CE&KS\7656400341020110
                       │                                       stack ksthunk | arturiausbmidiks | arturiausbmidi (oem11.inf)
                       ├ KeyLab 88 mk3 (MIDI Endpoint)  SWD\MIDISRV\MIDIU_KSA_16201702556534547415   (c_midi.inf, no driver)
                       ├ KeyLab 88 mk3 MIDI  SWD\MMDEVAPI\…_0_0   input
                       ├ KeyLab 88 mk3 DAW   SWD\MMDEVAPI\…_0_1   input
                       ├ KeyLab 88 mk3 MIDI  SWD\MMDEVAPI\…_1_0   output
                       └ KeyLab 88 mk3 DAW   SWD\MMDEVAPI\…_1_1   output
user mode: FL → winmm.dll → wdmaud2.drv → midisrv.exe (KSA transport) → the KS child above
```

[S:local for every line; the arrow order in the user-mode line is from G2 and the driver study.]

---

## The walk, one layer at a time

Each layer gives the look (a command or Device Manager clicks), what it printed here today, what it means, and the chapters it maps to.

### Layer 1. CPU root port (Chapters 0, 3 and 8)
- **Look:** `Get-PnpDeviceProperty -InstanceId 'PCI\VEN_1022&DEV_14DB&SUBSYS_14531022&REV_00\3&11583659&0&11' -KeyName DEVPKEY_Device_Stack,DEVPKEY_Device_LocationInfo,DEVPKEY_Device_MatchingDeviceId,DEVPKEY_Device_DriverRank | Format-Table KeyName,Data -Wrap`
- **Printed:**
  - "PCI Express Root Port", "PCI bus 0, device 2, function 1", ACPI path `…GPP7`.
  - Driver pci.inf, section PCI_BRIDGE, version 10.0.26100.8972.
  - Matched `PCI\CC_0604&DT_4`, rank 16719879 = `0x00FF2007`.
  - Stack `\Driver\pci | \Driver\ACPI | \Driver\pci` [S:local].
- **Meaning:**
  - This is a lane group on the 9950X3D's IO die feeding the chipset.
  - Class code 0604 means "PCI-to-PCI bridge". That ID is the bridge's own "compatible ID", like a CPUID feature flag (Chapter 8).
  - The same driver, pci.sys, sits at both ends of the stack. It is the bus driver that created this node (the bottom) and also the function driver that runs the bridge (the top). That is a clean Chapter 3 example of "bus driver vs function driver" [I].

### Layer 2. Chipset PCIe switch (Chapters 0 and 8)
- **Look:** the same command on `PCI\VEN_1022&DEV_43F4…\4&2c14e217&0&0011` (upstream port) and `PCI\VEN_1022&DEV_43F5…\5&2b8b9e2f&0&600011` (downstream port).
- **Printed:**
  - Upstream port: bus 7, with 7 downstream ports beneath it.
  - The KeyLab's downstream port: bus 8, device 12, location `#PCI(0C00)`, ACPI `…UP00.DP60`.
  - A second 43FD controller sits behind downstream port 08.0, which is the second chipset chip [S:local].
- **Meaning:** a byte from the keyboard crosses the CPU-to-chipset uplink and one switch. That is irrelevant to MIDI bandwidth [I]. The path matches the curriculum's reading; the second chip is new.

### Layer 3. The USB host controller (xHCI) (Chapters 4 and 7)
- **Look:**
  - `pnputil /enum-devices /instanceid "PCI\VEN_1022&DEV_43FD&SUBSYS_11421B21&REV_01\6&2766d23f&0&00600011" /resources`
  - Device Manager: Universal Serial Bus controllers → "AMD USB 3.20 eXtensible Host Controller - 1.10 (Microsoft)" → Resources tab.
- **Printed** [S:local]:
  - Stack `USBXHCI | ACPI | pci`, usbxhci.inf 10.0.26100.8972.
  - Rank 8396806 = `0x00802006`: feature score 0x80 (`FeatureScore=80` in usbxhci.inf), and compatible ID #6 `PCI\CC_0C0330` matched.
  - **8 interrupt resources, IRQ -126 to -133**, and **one memory window, 0xDD100000 to 0xDD107FFF (32 KB)**.
  - `MSISupported = 1`.
  - USBXHCI.SYS imports `WDFLDR.SYS`; driverquery shows `Ucx01000` Running.
- **Meaning:**
  - The 32 KB window is the controller's register file: where the driver rings doorbells and finds the event-ring pointers [S: X1; I for the mapping].
  - The negative IRQ numbers are message-signalled interrupts, and there are 8 vectors, so completions can land on several cores [I]. This is Chapter 4's "the controller interrupts the CPU, never the keyboard", made concrete.
  - Chapter 7: Microsoft's controller driver is KMDF plus a class extension, UCX (the "USB Controller Extension"). Like ks.sys, it never appears as a stack layer.

### Layer 4. The root hub (Chapter 3)
- **Look:** `Get-PnpDeviceProperty -InstanceId 'USB\ROOT_HUB30\7&397afaa3&0&0' -KeyName DEVPKEY_Device_Stack,DEVPKEY_Device_Children,DEVPKEY_Device_DriverRank`
- **Printed** [S:local]:
  - Stack `USBHUB3 | ACPI | USBXHCI`, rank `0x00800002`: hardware ID #2 `USB\ROOT_HUB30` matched, with feature score 0x80.
  - Children: a 2.0 hub (port 7), the GIGABYTE RGB device (port 11), and the KeyLab (port 8).
  - UsbHub3.sys imports `WDFLDR.SYS`.
- **Meaning:**
  - USBXHCI is the bus driver that invents the root hub.
  - USBHUB3 is its function driver, and in turn the bus driver for everything plugged into its ports, including the KeyLab.

### Layer 5. The KeyLab's USB node: Thesycon's main driver (Chapters 3, 5, 6 and 8)
- **Look:**
  - The curriculum's look-kit command 1 (it works as written).
  - `pnputil /enum-devices /instanceid "USB\VID_1C75&PID_02CE\7656400341020110" /drivers /stack /relations`
  - `pnputil /enum-devicetree "USB\VID_1C75&PID_02CE\7656400341020110" /stack /drivers`
  - Device Manager: View → Devices by type → "Arturia USB MIDI Devices" (the category name comes from oem22.inf's `[ClassInstall32]`) → KeyLab 88 mk3 → Details tab. Then switch View → Devices by connection to see its ancestors; I recall the selection is kept [I].
- **Printed** [S:local]:
  - **Driver:**
    - Class `arturiausbmidi_sc`, service `arturiausbmidi`, oem22.inf section `_Install_12.NTamd64`, provider Arturia 1.7.0.0.
    - PowerShell shows the date as "8/19/2025 8:00 PM" and pnputil shows "08/20/2025". INF dates are midnight UTC shown in local time [I].
    - Rank `00FF0001`, matching ID `USB\VID_1C75&PID_02CE`.
  - **IDs:**
    - Hardware IDs: `USB\VID_1C75&PID_02CE&REV_1500 | USB\VID_1C75&PID_02CE`.
    - 7 compatible IDs ending `USB\COMPOSITE`.
    - The bus-reported description "KeyLab 88 mk3" is the device's own product string [I].
  - **Location:**
    - Location: `Port_#0008.Hub_#0002`, path `…#USBROOT(0)#USB(8)`, BIOS name `\_SB.PCI0.GPP7.UP00.DP60.XH00.RHUB.POT8`.
    - Kernel object name (PDO): `\Device\USBPDO-11`.
  - **Capabilities:** 148 = 0x94 = Removable (0x04) + UniqueID (0x10) + SurpriseRemovalOK (0x80), decoded with cfgmgr32.h from the local SDK.
  - **Dates:** first seen 2025-11-17 10:43; current driver installed 2026-06-11 21:32; last arrival 2026-10-26 23:31:45.
  - **Children:** only the KS child. **There are no `MI_xx` interface children.** Get-PnpDevice over every `USB\VID_1C75*` instance, including past ones, returns only this node.
  - **Device interfaces:**

    | GUID | Status | What it is |
    |---|---|---|
    | {A5DCBF10…} | enabled | `GUID_DEVINTERFACE_USB_DEVICE`, Windows' generic "a USB device is here" door (usbiodef.h) |
    | {B68E4561…} | enabled | Same GUID as the `InterfaceGUID` value Arturia's INF writes, so this is TUSBAudio's private control door, which the API DLL opens [I] |
    | {B68E4562…} | disabled | Role unknown; the driver study's strings suggest a firmware-update (DFU) door [I] |
    | {FD0505C2…} | disabled | Role unknown |

  - **Device Parameters:** `DFUProtocol=2`, `InterfaceGUID`, `KsSampleRateControl=2`, `RestoreClockSourceAtStart=1`, `RestoreSampleRateAtStart=1`, `EnumerationRetryCount=0`, `SymbolicName`, `FriendlyDeviceNameString`.
    - Its `Ceip` subkey holds `DeviceInformation=8` and `DescriptorValidationInfo2=0x10000`, with the rest 0. These are undocumented [I].
  - **usbflags:** four revisions recorded (0500, 1101, 1201, 1500), each with `osvc = 00 00`, meaning no Microsoft OS descriptor.
  - **Physical location:** the BIOS-reported location buffer (ACPI `_PLD`) is `82 00 00 00 08 00 0E 00 A9 8C 00 02 01 00 00 00 FF FF FF FF`. Decoded with the ACPI layout, it says a user-visible, ejectable port on the back panel [I; BIOS tables are often boilerplate].
- **Meaning:**
  - Arturia's driver is the function driver for the whole device, so Windows' composite splitter (usbccgp) never loads.
  - ACPI is in the stack because the BIOS describes port 8 as an ACPI object (POT8). It supplies location and power data and stays out of the MIDI path [I].
  - "UniqueID" means the instance ID is the serial number, so a driver choice follows the keyboard to any port [S: M1 says devices without serial numbers lose their choice; S:local].
  - `osvc = 00 00` means WinUSB will never bind automatically [S:local; I].

### Layer 6. The kernel-streaming child that Thesycon invents (Chapters 3 and 10)
- **Look:** `pnputil /enum-devices /instanceid "TUSBAUDIO_ENUM\VID_1C75&PID_02CE&KS\7656400341020110" /drivers /stack`. Device Manager: Sound, video and game controllers → KeyLab 88 mk3.
- **Printed** [S:local]:
  - Class MEDIA, service `arturiausbmidiks`, oem11.inf `_Install_12.NTamd64`.
  - Rank `00FF0001`: hardware ID #1 `TUSBAUDIO_ENUM\VID_1C75&PID_02CE&KS` matched.
  - Stack `ksthunk | arturiausbmidiks | arturiausbmidi`. ksthunk comes from the MEDIA class `UpperFilters=ksthunk`.
  - It arrived 2 s after the USB node.
  - **Interfaces:** each MIDI pin is registered twice:
    - `midi_out_00_00` "MIDI" and `midi_out_01_01` "DAW" in KSCATEGORY_AUDIO plus **KSCATEGORY_RENDER**;
    - `midi_in_00_00` and `midi_in_01_01` in KSCATEGORY_AUDIO plus **KSCATEGORY_CAPTURE**. The GUIDs come from the local ks.h and ksmedia.h.
  - The "Topology" interface "USB Audio Mixer" is disabled.
  - Imports: arturiausbmidiks needs ntoskrnl, HAL and ks.sys; ksthunk needs ntoskrnl and ks.sys.
- **Meaning:**
  - "Render" is PC to keyboard (LED and screen writes); "capture" is keyboard to PC (keys and pads).
  - The upper Arturia driver has no USB code at all. It hands everything to its parent, arturiausbmidi, which here plays the bus-driver role (Chapter 3).
  - Audio is disabled because this is a MIDI-only device [I; matches the "Audio Controller initialization failed" event].

### Layer 7. The Windows MIDI Services endpoint (Chapters 2 and 10)
- **Look:**
  - `pnputil /enum-interfaces /class "{e7cce071-3c03-423f-88d3-f1045d02552b}" /properties`
  - `Get-Service midisrv`
  - `Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\Windows MIDI Services\Transport Plugins'`
- **Printed** [S:local]:
  - `SWD\MIDISRV\MIDIU_KSA_16201702556534547415`, class MidiEndpoint ("MIDI Endpoints", from c_midi.inf).
  - Driver section **`NO_DRV`**, stack `\Driver\SoftwareDevice` only. Rank `0x00FF0000`: hardware ID #0 `MIDISRV\MidiEndpoints` matched.
  - **Interface properties:**
    - transport GUID {0f273b18…}, which is `Midi2KSAggregateTransport`;
    - transport code "KSA", manufacturer "Arturia";
    - a pin table naming the four `midi_in/out_0x_0x` pins;
    - group names "KeyLab 88 mk3 MIDI" and "KeyLab 88 mk3 DAW 2".
  - **Transports registered** (all Enabled=1): KSA, KS, Loopback, Virtual. `Midi2DiscoveryEnabled=1`.
  - **midisrv:** Type 16, Start 3, Running, process 45480, started 2026-10-22 03:18:55.
- **Meaning:**
  - This node has no kernel driver. It is a software device that midisrv publishes so apps can find the endpoint.
  - midisrv is a user-mode process (Type 16), not a kernel driver (Type 1), which is Chapter 2's fenced yard.
  - It kept running through the 10-26 recovery (finding 7 above).

### Layer 8. The WinMM port nodes and names FL sees (Chapter 10)
- **Look:**
  - `pnputil /enum-devicetree "USB\VID_1C75&PID_02CE\7656400341020110"` lists the four software nodes.
  - Device Manager: Software devices; may need View → Show hidden devices [I].
  - For names: from `E:\AI-Setup`, `py -m arsenal.keylab ports`. It makes the same `midiInGetDevCapsW` calls (`arsenal/keylab/winmidi.py` lines 65-71) plus a service-state read [S:local code; I did not run it]. Or run my 30-line script, which opens no port.
- **Printed** [S:local]:
  - `_0_0` and `_0_1` carry `DEVINTERFACE_MIDI_INPUT {504BE32C…}`; `_1_0` and `_1_1` carry `DEVINTERFACE_MIDI_OUTPUT {6DC23320…}` (both defined in the local SDK's mmdeviceapi.h).
  - c_swdevice.inf, rank `0x00FF3000`.
  - Drivers32: `midi1=wdmaud2.drv`, `midi=wdmaud.drv` (legacy), `midimapper=midimap.dll`, `MidisrvTransferComplete=1`.
  - WinMM caps: the table in finding 6. Manufacturer 1; products 25, 26 and 27 = `MM_MSFT_GENERIC_MIDIIN/MIDIOUT/MIDISYNTH`; technology `MOD_MIDIPORT`, or `MOD_SWSYNTH` for the synth. All decoded with the local mmreg.h and mmeapi.h.
- **Meaning:**
  - In the node suffix, the first digit is direction (0 = into the PC, 1 = out) and the second is the port (0 = MIDI, 1 = DAW). This confirms the curriculum's cable reading.
  - The names come from the device's own descriptors through Thesycon's pins [S: driver study]. After any driver switch they may change, and FL's settings and our name lookup would need checking [S: G2 citing the Image-Line forum; I].

### Layer 9. The user-mode chain (Chapters 1 and 2)
- **Printed** [S:local]:
  - winmm.dll 10.0.26100.1 → wdmaud2.drv 10.0.26100.7705 "Windows MIDI Services WinMM service interface driver" → midisrv.exe 10.0.26100.7705.
  - All are signed "Microsoft Windows".
- **Meaning:** "driver" in `wdmaud2.drv` is just a DLL that runs inside FL's process. The word is overloaded (Chapter 1).

---

## The driver store, ranked against the KeyLab (Chapters 5 and 6)

**Look:**
- `pnputil /enum-drivers /class "{463bf520-cdd6-42c5-8602-d96558779b60}" /files /ids /devices`
- `pnputil /enum-drivers /class MEDIA /devices`
- `Get-ChildItem C:\Windows\System32\DriverStore\FileRepository -Directory | Where-Object Name -match '^(arturia|usbmidi2|wdma_usb|usbaudio2|usb\.inf|winusb|c_midi)'`

There are 244 third-party packages in the store [S:local].

| Package | What it is [S:local] | IDs it names | Against the KeyLab |
|---|---|---|---|
| oem22.inf (arturiausbmidi.inf) | Arturia 1.7.0.0, signer "Microsoft Windows Hardware Compatibility Publisher", attributes "Universal, Attested". File `arturiausbmidi.sys` 434,320 B, "TUSBAudio Class Driver" 5.72.0.0, catalog-signed Valid | `USB\VID_1C75&PID_02CE` (KeyLab line 52) | Parent: `00FF0001`, installed [S:local] |
| oem11.inf (arturiausbmidiks.inf) | Same signer. `arturiausbmidiks.sys` 55,440 B, "TUSBAudio Kernel Streaming Driver" 5.72.0.0 | `TUSBAUDIO_ENUM\VID_1C75&PID_02CE&KS` | KS child only: `00FF0001` [S:local] |
| usb.inf (in-box) | usbccgp.sys 10.0.26100.8972 | `USB\COMPOSITE` | Parent: `00FF2006`, outranked [S:local] |
| wdma_usb.inf (in-box) | usbaudio.sys 294,912 B, WDM + KS; loaded now for the NZXT mic and the webcam | `USB\CLASS_01`; excludes `…Prot_20` | Child only: predicted `00FF2005` [I] |
| usbmidi2.inf (in-box) | USBMidi2.sys 106,496 B, "ACX v1.0 MIDI 2 Driver", 10.0.26100.9168, `KmdfLibraryVersion = 1.31`. **No service key, so it has never been bound here** | `USB\CLASS_01&SUBCLASS_03&PROT_00`, then compatible `…SUBCLASS_03`, `USB\CLASS_01` | Child only: predicted `00FF3105` (AudioControl first) or `00FF2003` (MIDIStreaming alone) [I] |
| usbaudio2.inf (in-box) | Audio 2.0 | `USB\Class_01&SubClass_0x&Prot_20` only | No match expected for a USB-MIDI 1.0 device [I] |
| winusb.inf (in-box) | WinUsb.sys, KMDF; Stopped | `USB\MS_COMP_WINUSB`, `USB\Class_11…` (billboard), `USB\Class_ff&SubClass_42&Prot_01` (ADB) | **Never matches the KeyLab.** Reachable only by a manual pick or an INF of ours [S:local; I] |
| oem125.inf (novationusbmidi.inf) | Novation 2.29.0.77, Attested | 424 lines, all VID 1235 | Unrelated, but a second vendor MIDI driver to compare [S:local] |

**The rank, read off this machine's own numbers** [S:local values; S: L1/L2 rules, fetched]. The format is `0xSSGGTHHH`: signature score, then feature score, then identifier score. Lower wins.

| Node | Rank | What matched | T (match type) |
|---|---|---|---|
| KeyLab (Arturia) | 00FF0001 | device hardware ID #1 to INF hardware ID | 0 |
| MIDI endpoint | 00FF0000 | device hardware ID #0 to INF hardware ID | 0 |
| Root hub | 00800002 | hardware ID #2; feature score 80 from the INF | 0 |
| KeyLab (usb.inf candidate) | 00FF2006 | device compatible ID #6 `USB\COMPOSITE` to INF hardware ID | 2 |
| xHCI | 00802006 | compatible ID #6 `PCI\CC_0C0330`; feature score 80 | 2 |
| PCI bridges | 00FF2007 | compatible ID #7 | 2 |
| Past "USB Midi" child | 00FF2005 | compatible ID #5 `USB\Class_01` | 2 |
| WinMM nodes | 00FF3000 | compatible ID #0 to INF *compatible* ID. c_swdevice.inf's line is `SoftwareDevice,,SWD\GenericRaw`, with an empty hardware-ID slot | 3 |

Three of the four match types appear on this PC.

**Tie-breaks** are "the most recent date", then "the highest version", then any [S: selection overview, fetched].

---

## Signing posture (Chapter 6) [S:local]
- **Secure Boot is on:** `UEFISecureBootEnabled=1`.
- **The hypervisor is up but memory integrity is off:** `VirtualizationBasedSecurityStatus=2`, `SecurityServicesRunning=0` [I: Win32_DeviceGuard enumeration meanings].
- `CodeIntegrityPolicyEnforcementStatus=2`.
- `VulnerableDriverBlocklistEnable=1`.
- **Every Microsoft binary in the path is signed "Microsoft Windows".** Arturia's .sys files are catalog-signed by Microsoft's hardware publisher.
- This matches the curriculum: a kernel driver of our own needs Microsoft's signature or Secure Boot off. A WinUSB route reuses Microsoft's signed .sys and needs only a trusted catalog for our INF [S: L6, L8].

## Framework tally (Chapter 7) [S:local import tables]

| Driver | Imports | Model |
|---|---|---|
| arturiausbmidi | ntoskrnl, HAL, USBD | WDM |
| arturiausbmidiks | ntoskrnl, HAL, ks | WDM / AVStream |
| ksthunk | ntoskrnl, ks | WDM filter |
| usbccgp | ntoskrnl, WMILIB, USBD, WppRecorder | WDM |
| usbaudio | ntoskrnl, HAL, USBD, ks, WMILIB, WppRecorder | WDM + KS |
| USBMidi2 | ntoskrnl, USBD, WDFLDR | KMDF; ACX binds through the framework, so there is no direct ks import |
| WinUsb | ntoskrnl, HAL, USBD, WppRecorder, WDFLDR | KMDF |
| UsbHub3 | ntoskrnl, WppRecorder, ksecdd, USBD, WDFLDR | KMDF |
| USBXHCI | ntoskrnl, HAL, WppRecorder, WDFLDR | KMDF, plus the UCX extension |

Chapter 1's predict answer gains two hidden helpers: Ucx01000 and the KMDF runtime.

---

## The toggle on this machine (capstone grounding; the design belongs to another lane)

- **"Arturia" position:** today's state. Firmware updates need it: `DFUProtocol=2` is on this node, and the {B68E4561} control door is open [S:local; S: driver study].
- **"Windows native" position:**
  - Parent → USB Composite Device. This is already in the list.
  - Then a predicted `MI_00` audio-function child gets usbaudio automatically, or USBMidi2-ACX by hand.
  - Thesycon's KS child, the KSA endpoint and the four WinMM nodes would disappear, and new ones would appear with possibly new names.
  - Any extra interface (DFU or vendor) would get its own `MI_xx` child with no driver, a yellow mark in Device Manager, because there is no OS descriptor and no in-box match [I; S: M1].
  - Microsoft warns that "There's a Plug and Play bug in Windows right now that can put the old driver back after an update" [S: M1, fetched].
- **"Ours" position:**
  - It is not in any list today. It needs an INF of ours with a trusted catalog, or a manual pick of WinUSB.
  - The rank rules in finding 3 decide whether it stays put by itself or needs picking every time.
  - Our process must then republish ports (Chapter 11).
- **Device Manager's "Update driver → Browse → Let me pick" list is the same list pnputil shows,** but it ends in a switch button. For looking, use `pnputil … /drivers`, which cannot change anything [I].

## Look kit (all read-only; outputs as printed tonight are above)

1. **Walk the tree:**
   ```
   $id='USB\VID_1C75&PID_02CE\7656400341020110'; while($id -notlike 'HTREE*'){ $d=Get-PnpDevice -InstanceId $id; '{0} [{1}] {2}' -f $d.FriendlyName,$d.Service,$id; $id=(Get-PnpDeviceProperty -InstanceId $id -KeyName DEVPKEY_Device_Parent).Data }
   ```
2. **The subtree with stacks and drivers:** `pnputil /enum-devicetree "USB\VID_1C75&PID_02CE\7656400341020110" /stack /drivers`
3. **The toggle's positions:** `pnputil /enum-devices /instanceid "USB\VID_1C75&PID_02CE\7656400341020110" /drivers`
4. **Controller registers and interrupts:** `pnputil /enum-devices /instanceid "PCI\VEN_1022&DEV_43FD&SUBSYS_11421B21&REV_01\6&2766d23f&0&00600011" /resources`
5. **What the class drivers would claim:** `Select-String -Path C:\Windows\System32\DriverStore\FileRepository\usbmidi2.inf_*\usbmidi2.inf,C:\Windows\System32\DriverStore\FileRepository\wdma_usb.inf_*\wdma_usb.inf -Pattern 'USB\\CLASS_01'`
6. **Past and present class-driver bindings (the precedent):**
   ```
   Get-PnpDevice | Where-Object { $_.Service -in 'usbaudio','USBMidi2','usbccgp' } | Select-Object FriendlyName,Service,Present,InstanceId
   ```
7. **Which drivers are loaded:**
   ```
   driverquery /v /fo csv | ConvertFrom-Csv | Where-Object { $_.'Module Name' -match 'arturia|ksthunk|usbaudio|usbccgp|WINUSB|USBXHCI|USBHUB3|Ucx' } | Select-Object 'Module Name',State
   ```
8. **WinMM names:** `py -m arsenal.keylab ports` (from `E:\AI-Setup`).
9. The curriculum's look kit, commands 1 to 5, all still apply.

## Not read tonight, and what would read it
- **The KeyLab's interfaces, endpoints, IAD and USB speed** decide the usbaudio-versus-USBMidi2 outcome and the "ours" design. The descriptors and speed need the admin `logman` trace with rundown events, or USBView, both on the driver study's §2.6 approval list. The meaning of `Ceip DeviceInformation=8` is undocumented.
- **The "native" children are predicted, not observed.**
- Not re-read tonight: setupapi.dev.log and the two minidumps.
- **No new downloads are proposed;** the driver study's §2.6 list stands. Nothing was downloaded.

## Files (scratch, read-only helpers)
- `<scratch>\walk.ps1` and `walk.txt` (the full property dump)
- `…\scratchpad\winmm_names.py` (WinMM listing, opens no port)
- `…\scratchpad\pe_imports.py` (import-table reader)

## Sources
- **Microsoft Learn, fetched tonight:**
  - Identifier Score: https://learn.microsoft.com/en-us/windows-hardware/drivers/install/identifier-score--windows-vista-and-later-
  - Signature Score: https://learn.microsoft.com/en-us/windows-hardware/drivers/install/signature-score--windows-vista-and-later-
  - How Windows Ranks Driver Packages: https://learn.microsoft.com/en-us/windows-hardware/drivers/install/how-windows-ranks-driver-packages
  - Overview of the Driver Package Selection Process: https://learn.microsoft.com/en-us/windows-hardware/drivers/install/overview-of-the-driver-selection-process
  - Support for Interface Collections: https://learn.microsoft.com/en-us/windows-hardware/drivers/usbcon/support-for-interface-collections
- **Windows MIDI Services KB, fetched tonight (M1):** https://microsoft.github.io/MIDI/kb/how-to-switch-between-class-drivers/
- **Local Windows SDK 10.0.26100.0 headers:** mmdeviceapi.h, mmreg.h, mmeapi.h, ks.h, ksmedia.h, usbiodef.h, cfgmgr32.h.
- **Local INFs:** oem22, oem11, usbmidi2, wdma_usb, usbaudio2, winusb, usb, c_midi, c_swdevice, usbxhci, usbhub3, oem125.
- **Cited from the curriculum's references:** U2 (USB-MIDI 1.0 spec), X1 (xHCI spec), Z1 (libwdi), L6 (driver signing policy), L8 (PnP signing requirements).
- **Our own documents:**
  - G1: `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-hang-study-2026-10-26.md`
  - G2: `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-dev-guidance-and-hang-guide-2026-10-27.md`
  - The driver study: `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-driver-study-2026-10-27.md`
  - The house's port listing: `E:\AI-Setup\arsenal\keylab\winmidi.py` and `E:\AI-Setup\arsenal\midiports.py`

---

## The concept track (verbatim)

# Drivers course, concept track: how drivers work, with Daniel's KeyLab as the example (2026-10-27)

Below are 12 chapters and a capstone that ties them back to Daniel's toggle question. Each chapter has five parts: the idea in plain words, a hardware analogy, the precise version (one level deeper), a predict-before-you-look question with a read-only way to look, and a teach-back prompt. Each chapter is sized for one Forest Walk.

Grades used throughout:
- **[S]** a cited source says it. Sources fetched tonight are marked "fetched"; the rest are cited from standard references.
- **[S:local]** I measured it read-only on this PC tonight.
- **[I]** my inference.

`research/reviewed/keylab-liberation-2026-10-22/keylab-driver-study-2026-10-27.md` does not exist yet, so I worked from the hang study and the hang guide.

**What I did, all read-only:**
- Get-PnpDevice and Get-PnpDeviceProperty on the KeyLab, its parents and its children.
- `pnputil /enum-drivers`.
- Read the INF text of oem22, oem11, usbmidi2 and wdma_usb.
- Read the version and import strings of four driver binaries, plus their Authenticode status.
- Read registry values: service keys, Device Parameters, Secure Boot state, the code-integrity configuration, Drivers32 and the xHCI controller's MSI flag.
- Read the System log for bugcheck events and listed the minidump folder.
- Fetched 14 web pages.

I did not touch any KeyLab port or device handle or FL. I installed, changed and downloaded nothing, made no repo edits, and never left the repository directory.

## What tonight's look found (these shape the course and the toggle)

1. **The KeyLab's driver is Thesycon's TUSBAudio under Arturia's name.**
   - `arturiausbmidi.sys` reports ProductName "TUSBAudio Class Driver", file version 5.72.0.0, © 2009-2024. The package version is Arturia's 1.7.0.0 [S:local].
   - Its child driver `arturiausbmidiks.sys` is the "TUSBAudio Kernel Streaming Driver" and contains the string `tusbaudioks.sys` [S:local].
   - It is a classic WDM driver, not a framework (KMDF) driver: its import strings name ntoskrnl, hal and usbd, and no wdfldr [S:local]. Thesycon describes TUSBAudio as a "standard WDM/DirectX compatible sound device" [S: T1, fetched].
2. **Arturia's driver claims the whole USB device by its exact ID.**
   - The INF line is `"KeyLab 88 mk3" = _Install_12,USB\VID_1C75&PID_02CE` [S:local].
   - Microsoft says that matching a composite device's own ID "prevents the generic parent driver from loading" [S: L4, fetched].
   - So any toggle lives on the parent node: Arturia's driver on one side; on the other, Microsoft's generic parent (usbccgp) plus a driver on each interface [I].
3. **Both of Microsoft's MIDI class drivers are already in the driver store.**
   - `usbmidi2.inf` (KMDF 1.31, "ACX v1.0 MIDI 2 Driver") names `USB\CLASS_01&SUBCLASS_03&PROT_00` first. `wdma_usb.inf` (usbaudio.sys) names `USB\CLASS_01` [S:local].
   - `USBMidi2` has no service key, so it has never been bound to any device on this PC [S:local].
4. **Daniel's instinct about firmware updates has a real basis.**
   - Arturia's INF writes `DFUProtocol = 2` into the KeyLab's device key, and the value is there now [S:local].
   - Thesycon's driver advertises "Firmware upgrade according to DFU device class" [S: T1, fetched].
   - Whether Arturia's KeyLab updater uses that path or plain SysEx is unverified [I].
5. **Kernel signing on this PC is strict.**
   - Secure Boot is on. No TESTSIGNING appears in the boot options. The vulnerable-driver blocklist is on [S:local].
   - So a custom kernel driver needs either Microsoft's signature (an EV certificate plus Partner Center attestation) or Secure Boot turned off for test mode [S: L6, L7, fetched].
6. **This PC has two real blue screens, and both are good teaching material.** These are local times; the minidumps are in `C:\Windows\Minidump` [S:local].
   - `0x9F` with parameter 1 = 3 on 2026-10-21 20:05. The meaning of 0x9F/3 is "a device object has been blocking an IRP for too long a time" [S: L9].
   - `0x133` with parameter 1 = 0 on 2026-08-20 11:13. The meaning of 0x133/0 is "a single DPC or ISR exceeded its time allotment" [S: L10].
   - Which drivers caused them is unknown until someone reads the dumps.
7. **Correction to the brief.** The brief says oem41.inf installed the KS child node. On this PC the KS child is **oem11.inf** (arturiausbmidiks.inf) and the USB node is **oem22.inf** (arturiausbmidi.inf). The store holds no oem41 Arturia package [S:local].

---

## Chapter 0: The map (the KeyLab's family tree on this PC)

The whole course keeps coming back to this tree. Every line was measured tonight [S:local]. Stacks are listed top to bottom, so the bottom name is the driver that created the node.

```
Ryzen 9 9950X3D, PCIe root port GPP7  (PCI 00:02.1)
 └─ chipset PCIe switch: "600 Series Chipset PCIe Switch Downstream Port" 1022:43F5   [P1]
     └─ xHCI controller 1022:43FD "800 Series Chipset USB 3.x XHCI Controller"   stack: USBXHCI | ACPI | pci
         └─ USB Root Hub (USB 3.0)                                               stack: USBHUB3 | ACPI | USBXHCI
             └─ port 8: KeyLab 88 mk3  USB\VID_1C75&PID_02CE&REV_1500             stack: arturiausbmidi | ACPI | USBHUB3   (oem22.inf)
                 └─ TUSBAUDIO_ENUM\VID_1C75&PID_02CE&KS  (a child the driver invents)  stack: ksthunk | arturiausbmidiks | arturiausbmidi   (oem11.inf)
                     ├─ SWD\MIDISRV\MIDIU_KSA_16201702556534547415      the Windows MIDI Services endpoint (c_midi.inf)
                     └─ SWD\MMDEVAPI\MIDIU_KSA_…_0_0 / _0_1 / _1_0 / _1_1   "KeyLab 88 mk3 MIDI" and "KeyLab 88 mk3 DAW" (c_swdevice.inf)
```

The location path is `PCIROOT(0)#PCI(0201)#PCI(0000)#PCI(0C00)#PCI(0000)#USBROOT(0)` [S:local]. Read as a route, it goes CPU root port → chipset upstream port → downstream port → xHCI. So the keyboard reaches the CPU through the chipset's PCIe uplink, not through USB on the CPU's IO die [I].

---

## Chapter 1: What a driver is, and why the OS needs one

**The idea.** Windows speaks a few generic verbs: open, read, write and "do this special thing". Every device speaks its own dialect. A driver translates between the two. It also tells Windows what the device is, how to power it, and what to do when it vanishes. Without a driver, Windows knows that something with vendor 1C75 and product 02CE is on port 8, and can do nothing with it.

**The analogy.** Think of AMD "FineWine": the same Navi silicon got faster with driver updates, because the GPU driver is the compiler and scheduler between DirectX or Vulkan and the GPU's own command format. The API is the contract apps see; the GPU's ISA is the silicon's own language; the driver is the translator.
- For the KeyLab, the contract is "a MIDI port".
- The silicon's language is USB-MIDI packets plus Arturia SysEx.
- The translator is Thesycon's TUSBAudio with an Arturia label.

**Precise version (one level deeper).**
- In Windows a driver is a kernel module (a `.sys` file, which is a normal executable image). It is registered as a service of type 1 and attached as one layer of a device's stack [S: L15, B1].
  - On this PC, `arturiausbmidi` has Type=1 (kernel driver), while `midisrv` has Type=16 (a user-mode service in its own process) [S:local].
- A driver has three jobs: moving data (I/O), Plug and Play (start, stop, remove) and power [S: B1].
- Not every driver touches hardware.
  - `ksthunk` ("Kernel Streaming WOW Thunk Service") is a pure software filter that sits on every media-class device [S:local: service name; the MEDIA class UpperFilters value is `ksthunk`].
  - The word "driver" is also overloaded: `wdmaud2.drv` is a user-mode DLL inside each app, described as "Windows MIDI Services WinMM service interface driver" [S:local].

**Predict before you look.** How many kernel drivers that you could name sit between a Python LED write and the USB cable?
- **Look:** read the Stack lines in Chapter 0, or run the first command in the look kit.
- **Answer:**
  - Five named layers: ksthunk, arturiausbmidiks, arturiausbmidi, USBHUB3 and USBXHCI.
  - ACPI filters sit on the nodes but stay out of the data path [I].
  - Helper libraries such as usbd.sys and ks.sys never show up as layers [S:local; I].
  - Above all of them, in user mode: winmm.dll, wdmaud2.drv and midisrv.exe [S:local; S: G2].

**Teach-back.** Explain why a GPU driver update can make a game faster, but no KeyLab driver update can make a pad press arrive faster than USB allows.

---

## Chapter 2: User mode and kernel mode (rings, and why a kernel bug is a blue screen)

**The idea.** The CPU has privilege levels.
- Apps live in fenced yards (ring 3), each with its own private memory. When an app crashes, Windows sweeps up that one yard.
- The kernel and every driver share one big room (ring 0) with full access to memory and hardware. Nothing separates one driver's memory from another's.
- So when kernel code breaks, Windows cannot know what it damaged, and it stops the whole machine on purpose. That stop is a bugcheck, the blue screen.

**The analogy.** A machine-check exception. When the CPU finds an ECC error it cannot correct, it halts and logs to WHEA instead of computing on poisoned data. A bugcheck is the operating system's machine check: stopping is cheaper than silent corruption.

There is a middle path, and Daniel has lived it. The GPU driver model (WDDM) splits the display driver in two [S: L17]:
- A user-mode part that compiles shaders and builds command buffers. If it crashes, the game dies.
- A kernel-mode part that schedules work and manages VRAM.

When the GPU hangs, Timeout Detection and Recovery (TDR) resets the GPU instead of blue-screening the PC [S: L17]. That is a recovery ladder built into Windows. The KeyLab has nothing like it, which is why the 10-26 hang needed a power cycle [S: G1].

**Precise version.**
- On x86-64, the current privilege level lives in the code-segment register. The `syscall` instruction enters ring 0. Windows uses rings 0 and 3. The hypervisor (VBS) sits below the kernel, and AMD's Platform Security Processor sits below that [S: B1; I for the stacking picture].
- Kernel code also runs at interrupt request levels (IRQLs) [S: L14]:
  - PASSIVE (0) is normal thread work.
  - DISPATCH (2) is the level for scheduler work and deferred procedure calls (DPCs).
  - DIRQL is for interrupt handlers.
  - At DISPATCH or above, code may not wait or touch pageable memory. Breaking that rule is bugcheck 0xD1 or 0xA.

**Predict before you look.** If midisrv crashed tonight, what happens to FL and the KeyLab? And if `arturiausbmidi.sys` followed a bad pointer?
- **Look:** read the two services' Type values (look kit, command 5) and the bugcheck list (command 4).
- **Answer:**
  - A midisrv crash: MIDI apps lose their ports, and the service can start again because its start type is "on demand" (Start=3). The PC carries on [S:local; I].
  - A bad pointer in the driver: a bugcheck such as 0x50 or 0xD1, and the whole PC goes down [S: L10-family bugcheck reference; I].

**Teach-back.** Why does Windows blue-screen instead of just killing the bad driver? Use the machine-check analogy and the "one shared room" picture.

---

## Chapter 3: How a request travels (IRPs, device stacks, filter, function and bus drivers)

**The idea.** Every I/O operation becomes a packet called an I/O Request Packet (IRP). The IRP is handed down a stack of drivers attached to one device.
- Each layer can handle the request, change it, or pass it down.
- When the bottom layer finishes, the IRP climbs back up, and each layer gets a look on the way.
- The **bus driver** creates the bottom of a stack, which says "a device exists here". The **function driver** owns the device's behaviour. **Filters** slip in above or below the function driver.

**The analogy.** PCIe non-posted requests, and the KeyLab really does ride a PCIe switch.
- A memory-read TLP goes down through the root port and the chipset's switch to the endpoint, and a Completion TLP is routed back up.
- IRPs are all "non-posted": every one must eventually come back completed.
- A pending IRP is an outstanding tag. The 10-26 hang looks like an outstanding tag that never got its completion [I].

**Precise version.**
- A device node is built from a physical device object (PDO, from the bus driver), optional lower filters, a functional device object (FDO, from the function driver), and optional upper filters [S: L15].
- The I/O manager gives each IRP one stack location per layer. A driver passes the IRP down with `IoCallDriver`, and the bottom layer finishes it with `IoCompleteRequest`. Completion routines run on the way back up. `STATUS_PENDING` means "I'll finish later", and Windows allows that to last forever [S: B1].
- USB drivers talk to the hub with an internal-control IRP that carries a USB Request Block (a URB). `usbd.sys` among Arturia's imports is the helper for building URBs [S:local; S: L15].
- On this PC, `arturiausbmidi` plays two roles [S:local]:
  - It is the **function driver** on the USB node, with USBHUB3 as that node's bus driver.
  - It is the **bus driver** of its own invented child, `TUSBAUDIO_ENUM…&KS`, where arturiausbmidiks is the function driver and ksthunk an upper filter.
- An LED write, top to bottom:
  1. Python calls `midiOutLongMsg`, which goes through wdmaud2.drv to midisrv [S: G2].
  2. midisrv's kernel-streaming aggregate (KSA) transport makes a kernel-streaming write.
  3. The write passes ksthunk, then arturiausbmidiks, then arturiausbmidi.
  4. arturiausbmidi turns it into a URB for a bulk OUT transfer, which goes to USBHUB3, then USBXHCI, then the silicon.
  5. The completion climbs back up [S:local stacks; S: G2; I for the order inside Thesycon's code].
- Only some requests have watchdogs.
  - Power IRPs do. That is the 0x9F/3 blue screen from 10-21 [S:local; S: L9].
  - Ordinary reads and writes do not. That is why midisrv could wait on the KeyLab "with no time limit" (Pete Brown, microsoft/MIDI #1195) [S: G2].

**Predict before you look.** Will a stuck write IRP blue-screen the PC the way the 10-21 power IRP did?
- **Answer:** no. Pending forever is legal for ordinary I/O, which is why the hang was silent, and why our own tools need a watchdog [S: L9, G2; I].

Second prediction: Arturia's driver appears in two stacks. What role does it play in each?
- **Look:** read the two Stack lines (look kit, command 1).
- **Answer:** the function driver on the USB node, and the bus driver at the bottom of the KS child's stack [S:local].

**Teach-back.** Draw the KeyLab node's stack from memory. Say which driver created the bottom object (the PDO) and which owns the function object (the FDO).

---

## Chapter 4: Interrupts, DMA and polling

**The idea.** Hardware and CPU coordinate in three ways:
- **Polling:** keep asking "anything yet?"
- **Interrupts:** the device taps the CPU on the shoulder.
- **DMA (direct memory access):** the device moves data to and from RAM by itself and says when it's done.

A twist that surprises everyone: **a USB device can never interrupt anything.** The host controller polls it. The controller then DMAs the data into RAM and interrupts the CPU.

**The analogy.** GPU command queues. The driver writes commands into a ring buffer in RAM and rings a doorbell. The command processor fetches them by DMA, and completion comes back as a fence or interrupt.

The xHCI USB controller works the same way [S: X1]:
- **Transfer rings** of Transfer Request Blocks (TRBs), one per endpoint.
- A **doorbell** register per device.
- An **event ring** for completions.
- **MSI-X** interrupts. A message-signalled interrupt is just a memory write over PCIe [S: L18].

NVMe has the same shape, with submission and completion queues.

**Precise version.**
- The interrupt service routine (ISR) runs at device IRQL, does the minimum, and queues a DPC. The DPC runs at DISPATCH level and completes the IRPs [S: L14].
  - Windows has a DPC watchdog: one DPC or ISR running too long is bugcheck 0x133/0. That is this PC's 08-20 blue screen [S:local; S: L10].
- This PC's xHCI has `MSISupported = 1` [S:local].
- USB timing and flow control [S: U1, ch. 5 and 8]:
  - Full speed runs 1 ms frames; high speed runs 125 µs microframes.
  - A device answers an IN poll with data or NAK ("nothing yet"), and an OUT with ACK or NAK ("I'm busy").
  - NAK is flow control, not an error. A transfer the device keeps NAKing stays pending until software cancels it [S: U1; I for the phrasing].
  - A KeyLab that "stops draining its input" (#1084) would look exactly like an endless NAK on its bulk OUT endpoint [S: G2; I].
- Pad presses leave the keyboard only while the host has an IN read posted. Drivers keep reads permanently posted; KMDF calls this a "continuous reader" [S: L12/L13].
- The xHCI's DMA can be fenced by the IOMMU (AMD-Vi) [S: Kernel DMA Protection docs; I].

**Predict before you look.** When you hit a pad, does the KeyLab interrupt your CPU?
- **Answer:** no. It waits for the xHCI's IN poll. The controller writes the bytes to RAM and fires an MSI-X. That interrupt is the controller's, never the keyboard's [S: U1, X1].

Second prediction: was the 08-20 DPC blue screen the KeyLab's driver?
- **Answer:** unknowable without the minidump. Reading it needs WinDbg (see the downloads).

**Teach-back.** Explain the transfer ring, the doorbell and the event ring using only GPU words.

---

## Chapter 5: Plug and Play, and how Windows picks a driver

**The idea.** When a device arrives:
1. Its bus driver reports a list of IDs, from most specific to most generic.
2. Windows searches the driver store for INF files whose model lines name any of those IDs.
3. It scores every candidate and installs the lowest score.

Packages you add are copied into the store and renamed `oemNN.inf`.

**The analogy.** Code that picks a path by CPUID. A library carries an AVX-512 path, an AVX2 path and an SSE2 baseline, and picks the most specific one the chip supports.
- Hardware IDs are the exact family, model and stepping. `REV_1500` is the device's bcdDevice field, which matches firmware 1.5.0 [S: L11; I for the firmware mapping].
- Compatible IDs are feature flags, such as "speaks USB Audio, MIDI Streaming subclass".
- The driver store is the shelf of code paths, and the rank is the dispatcher's choice.

**Precise version.**
- A rank is `0xSSGGTHHH`: signature score, feature score, then identifier score. Lower wins [S: L1, L2, fetched]. Ties go to the newer date, then the newer version [S: L3].
- Decoding the KeyLab's `DriverRank = 16711681 = 0x00FF0001` [S:local; S: L1/L2]:

  | Part | Value | Meaning |
  |---|---|---|
  | SS | 00 | trusted signature |
  | GG | FF | no feature score set [S] |
  | T | 0 | a device hardware ID matched an INF hardware ID, the best match type |
  | HHH | 001 | the match was the second ID in the device's list, `USB\VID_1C75&PID_02CE` |

  A class driver can only match through compatible IDs, which score 0x2000 or worse. So while Arturia's package sits in the store, Arturia wins automatically [I from L1].
- The KeyLab's compatible-ID list ends with `USB\COMPOSITE` [S:local]. The hub reports that only when the device class is 0, there are several interfaces, and there is one configuration [S: L5, fetched].
  - Without Arturia's package, `usb.inf` would load `usbccgp`. That driver would split the device into children named `…&MI_00`, `…&MI_01` and so on, each carrying its own class IDs [S: L4, L5].
  - Arturia names the whole device instead, which Microsoft says keeps usbccgp out [S: L4].
- Files run straight from the store. The INF's `ServiceBinary = %13%\arturiausbmidi.sys` becomes `ImagePath = …\DriverStore\FileRepository\arturiausbmidi.inf_amd64_979f2262063c03d1\arturiausbmidi.sys` [S:local; S: L16].
- Arturia's INF covers 17 Arturia products. Two of them have twin product IDs (MiniLab 3 020B/220B, KeyStep Pro 0218/2218) [S:local]. What the twins mean is unknown [I].

**Predict before you look.** Microsoft ships two INFs that would both take a MIDI interface:
- `usbmidi2.inf` names `USB\CLASS_01&SUBCLASS_03&PROT_00, USB\CLASS_01&SUBCLASS_03, USB\CLASS_01`.
- `wdma_usb.inf` names `USB\CLASS_01` [S:local].

Which would win the KeyLab's MIDI interface?
- **Answer:** usbmidi2. Both are compatible-ID matches, but usbmidi2 hits the interface's first, most specific ID, at position 0, while wdma_usb hits position 2 [S: L1; I, because the KeyLab's interface IDs are unread]. This agrees with Microsoft's note that USBMidi2-ACX is now the default for class-compliant MIDI [S: M1, fetched].

**Teach-back.** Why will Windows keep choosing Arturia's driver even when Microsoft's is newer? (Rank comes before date: a hardware-ID match beats any compatible-ID match, and the date only breaks ties.)

**Where this touches the toggle.** Toggling means choosing a different package for the same device node. Both packages can sit in the store at once, so a toggle never needs a download [S: M1 describes Device Manager's "Let me pick" flow; I].

---

## Chapter 6: Driver packages and signing (INF, CAT, Authenticode, attestation, test signing, Secure Boot)

**The idea.** A driver package has three parts:
- the INF, which is the install recipe;
- the CAT file, a signed list of hashes for every file in the package;
- the binaries.

Windows checks the catalog before it stages the package, and checks kernel code again before loading it. On modern Windows with Secure Boot on, Microsoft itself must sign every kernel driver.

**The analogy.** Engineering samples versus retail chips.
- **WHQL** is full qualification: Microsoft's HLK test lab.
- **Attestation** is the vendor proving its identity with an EV certificate, and Microsoft scanning and countersigning without the full lab. Compare a vendor-declared EXPO profile with a QVL-tested memory kit.
- **Test signing** is ES mode: any certificate works, and a "Test Mode" watermark plays the part of the ES marking. Like an ES chip, it only runs where the board allows it.
- **Secure Boot** is a chain of trust: the PSP checks the firmware, the firmware checks the boot manager, and Windows checks every driver.

**Precise version.**
- Arturia's packages show signer "Microsoft Windows Hardware Compatibility Publisher" with the attributes "Universal, Attested". Their binaries carry no embedded signature and are verified through the catalog [S:local].
- Microsoft's own drivers are signed "Microsoft Windows" [S:local].
- Policy [S: L6, fetched]:
  - Since Windows 10 1607, Windows "will not load any new kernel-mode drivers which are not signed by the Dev Portal".
  - Getting a Dev Portal account requires an EV code-signing certificate.
  - Attestation covers Windows 10+ client systems without HLK testing.
  - One exception allows cross-signed drivers: "Secure Boot is off in the BIOS".
- Test mode [S: L7, fetched]:
  - The command is `Bcdedit -set TESTSIGNING ON`. With Secure Boot on it fails with "protected by Secure Boot policy".
  - Windows then shows a "Test Mode" watermark and accepts any certificate.
  - With memory integrity (HVCI) on, binaries must still be test-signed.
- This PC [S:local]:
  - Secure Boot is on, and the boot options contain no TESTSIGNING.
  - `VulnerableDriverBlocklistEnable = 1`.
  - The HVCI scenario key is absent, which suggests memory integrity is not configured [I].
- Code that runs in user mode, such as a WinUSB app or a UMDF DLL, is outside the kernel-mode signing rule. Its package catalog still has to pass the Plug and Play signing check, and a test certificate the machine trusts satisfies that check [S: L8, fetched; I for UMDF details]. This is how Zadig/libwdi installs WinUSB with a self-made certificate [S: Z1].

**Predict before you look.** Arturia's driver says "Arturia" everywhere. Whose signature is on it?
- **Look:** `pnputil /enum-drivers` (look kit, command 2).
- **Answer:** Microsoft's, through attestation [S:local].

Second prediction: what would it take to load a kernel driver of our own on this PC tomorrow?
- **Answer:** either Secure Boot off plus test mode, which is a system-setting change and Daniel's call because it weakens the machine, or an EV certificate plus a Partner Center attestation submission for every build [S: L6, L7; I].

**Teach-back.** Explain how a 15 KB catalog lets Windows trust a 434 KB driver that has no signature of its own.

---

## Chapter 7: KMDF and UMDF (and the WDM underneath)

**The idea.** A driver written from scratch must handle dozens of Plug and Play and power events correctly. That raw model is called WDM. Microsoft's frameworks (WDF) supply a runtime that runs those state machines for you, so you write only the device-specific parts.
- **KMDF** runs in the kernel.
- **UMDF** runs your driver in a separate user-mode host process. If it crashes, that process dies and the PC stays up.

**The analogy.**
- WDM versus KMDF is hand-written assembly versus a compiler plus runtime.
- UMDF is Zen 2's chiplet move. Putting the I/O and memory controller on a separate IO die cost a hop of latency but bought modularity and fault isolation. UMDF moves the driver out of the kernel into its own process: one hop slower per request, and a defect takes out one chiplet, not the package.

**Precise version.**
- KMDF provides framework objects such as WDFDEVICE, WDFQUEUE, WDFREQUEST and WDFUSBPIPE. They are loaded through `wdfldr.sys`, and the INF declares a `KmdfLibraryVersion` [S: L13].
- UMDF 2 uses the same object model, runs in `WUDFHost.exe`, and reaches the kernel through a reflector driver (WUDFRd.sys) [S: L13, B1].
- Microsoft's guidance: use UMDF when it can do the job, and KMDF when you need kernel-only abilities such as serving kernel-mode clients [S: L13].
- On this PC [S:local]:
  - `arturiausbmidi.sys` is WDM, with no wdfldr import. Thesycon also says WDM [S: T1].
  - `USBMidi2.sys` imports wdfldr.sys, its INF says `KmdfLibraryVersion = 1.31`, and it calls itself "ACX v1.0 MIDI 2 Driver". ACX is Microsoft's newer audio framework built on KMDF [S: Learn ACX overview].
  - `usbaudio.sys` is WDM plus kernel streaming (it imports ks.sys).

**Predict before you look.** Of the three USB-MIDI drivers on this PC (Arturia's, usbaudio and USBMidi2), which use a framework?
- **Answer:** only USBMidi2 [S:local].

**Teach-back.** MIDI is tiny data. Why might Microsoft still build its newest MIDI driver on KMDF rather than UMDF? (It plugs into the kernel's audio and kernel-streaming plumbing, which kernel clients use [I].)

---

## Chapter 8: USB from the wire up

**The idea.** USB is a bus the host runs. When you plug something in:
1. The hub notices and resets the port.
2. The host gives the device an address.
3. The host asks the device to describe itself (its descriptors).
4. The host picks a configuration.

A device is made of configurations; a configuration holds interfaces (the functions); an interface holds endpoints (one-way mailboxes). There are four transfer types:
- **control:** endpoint 0, for setup and commands;
- **bulk:** reliable, sent whenever there is room;
- **interrupt:** small, polled on a schedule;
- **isochronous:** reserved time and no retries, used for audio and video.

Class specifications (HID, Audio, MIDI) let one Microsoft driver serve every device that follows them.

**The analogy.** PCIe enumeration at boot, done hot.
- The BIOS walks the bus and reads each function's config space (vendor, device, class code). The USB host reads descriptors.
- Assigning BARs corresponds to SET_ADDRESS.
- The class codes are cousins: the xHCI's own hardware ID carries `CC_0C0330` (serial bus, USB, xHCI) [S:local], much as a MIDI interface carries class 01, subclass 03.
- A composite USB device is a multi-function PCIe device. The RX 9070 XT itself is a GPU function plus an HD Audio function under one PCIe address [S:local: two instances under one parent; I for the function numbering]. It even sits behind its own PCIe switch, AMD 1002:1478/1479 [S:local].
- USB 2.0 is a shared front-side bus with the host as the only arbiter. USB 3 SuperSpeed is point-to-point like PCIe, and every USB 3 port also carries a separate USB 2 pair [S: U1].

**Precise version.**
- Descriptors [S: U1, ch. 9]:
  - The device descriptor holds idVendor, idProduct, bcdDevice, bDeviceClass and bNumConfigurations.
  - The configuration descriptor contains interface descriptors (bInterfaceClass, SubClass, Protocol).
  - Endpoint descriptors give the address and direction, the transfer type, wMaxPacketSize and bInterval.
- Windows builds its IDs straight from these fields [S: L11; S:local]:
  - `USB\VID_1C75&PID_02CE&REV_1500` is idVendor, idProduct and bcdDevice.
  - `USB\DevClass_00` means "the class is set per interface".
  - `USB\COMPOSITE` means two or more interfaces and one configuration [S: L5].
- Speeds are 1.5, 12 and 480 Mb/s [S: U1]. The KeyLab's speed and actual descriptors are unread; reading them takes a descriptor tool, and that tool queries the device through the hub [I].

**Predict before you look.** What are the KeyLab's interfaces, judging only from its compatible IDs?
- **Expected answer:** at least two interfaces in one configuration. A class-compliant MIDI device pairs Audio Control (01/01) with MIDI Streaming (01/03), and the MIDI spec requires the Audio Control interface [S: U2]. There may also be a vendor interface (class FF) for Arturia's updater [I].
- **Look:** a descriptor dump, which needs Daniel's go (see the downloads).

**Teach-back.** Explain to Simon why a USB keyboard cannot push a keypress, and who decides when it leaves.

---

## Chapter 9: USB-MIDI 1.0 (4-byte event packets, cables, SysEx framing)

**The idea.** MIDI on a DIN cable is a stream of variable-length messages. USB-MIDI chops that stream into fixed 4-byte packets:
- one header byte that says which virtual cable and what kind of message;
- up to three MIDI bytes.

A SysEx message can be any length. It travels as a chain of packets marked "starts or continues", ending with one marked "ends here with 1, 2 or 3 bytes".

**The analogy.** x86 decoding.
- x86 instructions are 1 to 15 bytes long, so the front end works hard to find where each one starts. The core turns them into fixed-width micro-ops tagged with pre-decoded lengths.
- MIDI 1.0 bytes are the x86. USB-MIDI packets are the micro-ops. The Code Index Number (CIN) is the pre-decode tag. The cable number is like an SMT thread tag that lets two streams share one pipe.
- MIDI 2.0's packet format (UMP) is fixed-width from the start, at 32 to 128 bits: the RISC version [S: U3].
- The 12-per-100 ms burst governor fits this picture too. The wire is nowhere near full; the keyboard's small CPU is the bottleneck, the way a game can be CPU-bound on draw calls rather than GPU-bound [I].

**Precise version.**
- Byte 0 holds the cable number (high nibble, 0 to 15) and the CIN (low nibble) [S: U2, §4, Table 4-1]. The CIN values:

  | CIN | Bytes | Meaning |
  |---|---|---|
  | 2 | 2 | two-byte system common |
  | 3 | 3 | three-byte system common |
  | 4 | 3 | SysEx starts or continues |
  | 5 | 1 | SysEx ends with one byte, or single-byte system common |
  | 6 | 2 | SysEx ends with two bytes |
  | 7 | 3 | SysEx ends with three bytes |
  | 8 / 9 | 3 | note off / note on |
  | A | 3 | polyphonic pressure |
  | B | 3 | control change |
  | C | 2 | program change |
  | D | 2 | channel pressure |
  | E | 3 | pitch bend |
  | F | 1 | single byte |

- MIDI uses **bulk** endpoints [S: U2]. One 64-byte full-speed bulk packet carries up to 16 event packets [S: U1; arithmetic].
- Daniel's own bytes, encoded. The cable numbers are [I]: the WinMM nodes `_x_0` and `_x_1` suggest MIDI is cable 0 and DAW is cable 1.
  - **Device Inquiry** `F0 7E 7F 06 01 F7` (6 bytes) becomes `04 F0 7E 7F` + `07 06 01 F7`.
  - **The 17-byte reply** becomes five CIN-4 packets plus `06 vv F7 00`: 6 packets, 24 bytes on the wire.
  - **Pad 1 blue** is `F0 00 20 6B 7F 42 00 02 03 52 00 00 7F 00 F7`, 15 bytes built by `set_led` in `E:\AI-Setup\arsenal\keylab\protocol.py` [S:local]. It becomes `14 F0 00 20`, `14 6B 7F 42`, `14 00 02 03`, `14 52 00 00`, `17 7F 00 F7`.
  - **A pad press on the DAW port**, `99 00 7F` [S: G1], becomes `19 99 00 7F`. Its pressure sweep `A0 00 49` becomes `1A A0 00 49`.
- On a DIN cable at 31,250 baud (10 bits per byte), that 15-byte LED message takes 4.8 ms [S: MIDI 1.0 spec; arithmetic]. On USB it fits inside one 1 ms frame [I].
- The packing is done by the host driver and the device firmware; apps never see packets [I].
- SysEx data bytes must stay below 0x80, and our `sysex()` refuses anything else [S:local]. An unterminated SysEx makes Windows swallow the messages after it; a lone `F7` clears it [S: G2].

**Predict before you look.** How many packets does the Device Inquiry take, and what is the second packet's first byte?
- **Answer:** two; `07` on cable 0 or `17` on cable 1.

**Teach-back.** Hand-encode "pad 1 magenta".
- **Answer:** `14 F0 00 20 / 14 6B 7F 42 / 14 00 02 03 / 14 52 7F 00 / 17 7F 00 F7`.

---

## Chapter 10: The Windows MIDI and audio stack (WinMM, kernel streaming, Windows MIDI Services and midisrv, usbaudio, usbmidi2, vendor drivers)

**The idea.** Apps no longer talk to MIDI drivers directly. On this PC, every MIDI app goes through the Windows MIDI Services service (midisrv). The service:
- owns the one connection to each device and shares it among apps;
- converts between MIDI 1.0 bytes and MIDI 2.0 packets.

Below midisrv sit kernel-streaming (KS) drivers: Microsoft's class drivers for compliant devices, or a vendor's driver such as Arturia's Thesycon build.

**The analogy.** The IO die.
- Zen's core dies never touch DRAM or PCIe directly; everything crosses Infinity Fabric to the IO die, which arbitrates and translates. midisrv is the KeyLab's IO die. FL, the screen service and the CLI all share one device through it.
- The price is an extra hop and a single point of failure: when the service wedges, everyone wedges (#1084) [S: G2].
- KSA presents all of a device's KS pins as one MIDI 2.0 endpoint [S: M2, fetched].
- Thesycon is the reference board: Arturia ships Thesycon's driver with its own name on the box. Same die, different shroud.

**Precise version.**
- The path down:
  1. An app calls winmm.dll.
  2. winmm.dll loads `wdmaud2.drv` (Drivers32 `midi1=wdmaud2.drv`; legacy `midi=wdmaud.drv` is still listed) [S:local].
  3. wdmaud2.drv hands the message to midisrv. `midiOutLongMsg` is synchronous, uses 2,048-byte chunks and waits 1,000 ms for "send complete" [S: G2].
  4. midisrv's KSA transport passes it to the KS filter on `TUSBAUDIO_ENUM…&KS` (arturiausbmidiks, which imports ks.sys) [S:local].
  5. From there it goes to arturiausbmidi and onto USB.
- midisrv has other transports: loopback, virtual devices for apps, Bluetooth LE and network [S: M4, fetched].
- Microsoft's class drivers here [S:local]:
  - usbaudio.sys: WDM plus KS, for USB Audio 1.0 including MIDI.
  - usbaudio2.sys: Audio 2.0. `wdma_usb.inf` excludes the Audio 2.0 interface IDs (`…&Prot_20`) from usbaudio.
  - USBMidi2.sys: KMDF plus ACX.
- Microsoft's warning: "If a device needs a driver from its manufacturer, neither of these two drivers will work for it" [S: M1, fetched].

**Predict before you look.** When FL and our screen service both hold the DAW port, how many connections does the KeyLab's USB link carry?
- **Answer:** one. midisrv holds the device and multiplexes the apps above it [S: G2; I].

**Teach-back.** Where would you put probes to tell "midisrv is stuck" apart from "the driver or device is stuck"? (Compare the native endpoint monitor with a WinMM monitor, as in ladder step 3 of the hang guide; below the driver, use a USB capture [S: G2].)

---

## Chapter 11: User-mode drivers with WinUSB and libusb, and virtual ports (the "userspace driver")

**The idea.** You don't need kernel code to drive a USB device. Microsoft ships a generic kernel driver, WinUSB, that simply exposes a device's endpoints as pipes to a program. The program then speaks the device's protocol itself, here USB-MIDI packets. If other apps such as FL should still see the device, the program publishes virtual MIDI ports. That program is the "userspace driver".

**The analogy.** Mantle, then Vulkan and DX12.
- DX11 drivers did heavy lifting behind the app's back. AMD's Mantle, and after it Vulkan and DX12, made the driver thin and handed command buffers and synchronization to the app.
- WinUSB is the thin driver, libusb is a portable loader on top of it, and our program is the engine.
- You get freedom, and you take on responsibility: pacing, recovery and timeouts are now yours. That is exactly the watchdog the hang taught us we need.

**Precise version.**
- WinUSB is winusb.sys (Microsoft-signed) plus the winusb.dll API: `WinUsb_ReadPipe`, `WinUsb_WritePipe`, and `WinUsb_SetPipePolicy`, where `PIPE_TRANSFER_TIMEOUT` gives each transfer a deadline [S: L12]. That deadline is what midisrv's KS write lacked [S: G2; I].
- WinUSB gets bound to a device in one of two ways [S: L12]:
  - an INF that names the device or one interface;
  - Microsoft OS 2.0 descriptors in the device's own firmware, which the KeyLab's firmware would have to provide.
- libusb uses WinUSB underneath on Windows, and Zadig/libwdi generate the INF and a self-signed catalog [S: Z1].
- Only one function driver can own a device node. If WinUSB owns the MIDI interface, neither Arturia's driver nor a Microsoft class driver can [S: L4/L5 model; I].
  - Because Arturia's driver claims the whole device, a WinUSB route means first switching the parent to usbccgp, then giving the interface to WinUSB [I].
- FL then loses the KeyLab as hardware unless our program republishes ports [S: M3, fetched]:
  - Windows MIDI Services' **Virtual Device App** endpoints can only be created by apps built on its SDK.
  - WinMM apps like FL can connect to them, MIDI 1.0 only.
  - The endpoint closes when the owning app closes.
- There is a second form of "userspace driver" that swaps no driver at all: our own long-lived service owns the KeyLab's ports through Windows MIDI Services and republishes virtual ports to everyone else. `arsenal/keylab` already lives at that altitude [I].

**Predict before you look.** If WinUSB owned the KeyLab's MIDI interface, what would FL's MIDI settings show?
- **Answer:** no KeyLab ports, only whatever virtual ports our program publishes [I].

**Teach-back.** What does a userspace driver gain, and what must it now do that Thesycon's driver used to do?
- **Gains:** no kernel code, crash safety, timeouts, full visibility.
- **New duties:** packing and unpacking packets, keeping IN reads posted, recovering after an unplug, publishing ports, and losing the vendor's DFU path.

---

## Capstone: Daniel's toggle question through the course's eyes (concept only; the design belongs to another lane)

- **The "native" driver is Arturia's (Thesycon's).** It is probably the firmware-update path: `DFUProtocol = 2` plus Thesycon's DFU feature [S:local; S: T1; I that Arturia's updater uses it].
- **Where a switch can live:**
  1. **The binding on the KeyLab's device node** (Chapters 5 and 11). The choice is Arturia's driver versus usbccgp, with usbmidi2, usbaudio or WinUSB on each interface. Every package can sit in the store at once, so switching is re-selection, not installation.
     - Because of rank, Arturia's driver will win back the node whenever Windows re-chooses on its own [I from L1]. Whether that happens on a replug, and how to make a choice stick, is a design question to test.
  2. **Above the drivers** (Chapter 10). Keep Arturia's driver and put our userspace layer on top. This needs no toggle at all.
  3. **The firmware path.** Toggle back to Arturia's driver for updates, if the updater needs it.
- **Unknowns that decide the design.** Each is a predict-then-look, and each needs Daniel's go:
  - the KeyLab's descriptors: is it class-compliant, and is there a vendor interface?
  - what the updater talks over: DFU through the driver, or SysEx;
  - the device's USB speed;
  - whether it shows a different product ID during an update (Arturia's INF names only 02CE for this model [S:local]).

## Look kit (read-only commands Daniel can run in PowerShell)

1. Stack, IDs and rank:
   `Get-PnpDeviceProperty -InstanceId 'USB\VID_1C75&PID_02CE\7656400341020110' -KeyName DEVPKEY_Device_Stack,DEVPKEY_Device_HardwareIds,DEVPKEY_Device_CompatibleIds,DEVPKEY_Device_DriverRank,DEVPKEY_Device_DriverInfPath | Format-Table KeyName,Data -Wrap`
2. The driver store: `pnputil /enum-drivers`, then look for arturiausbmidi and usbmidi2.
3. Signing posture: `Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\SecureBoot\State'`
4. Blue screens: `Get-WinEvent -FilterHashtable @{LogName='System'; Id=1001; ProviderName='Microsoft-Windows-WER-SystemErrorReporting'} -MaxEvents 5 | Format-List TimeCreated,Message`
5. Kernel driver versus service: `Get-ItemProperty HKLM:\SYSTEM\CurrentControlSet\Services\midisrv, HKLM:\SYSTEM\CurrentControlSet\Services\arturiausbmidi | Select-Object PSChildName,Type,Start,ImagePath`

## Downloads for Daniel's approval (none done)

1. **Windows MIDI Services Tools 0.99.94-preview.12 (x64)**, 223,376,824 bytes, from github.com/microsoft/MIDI/releases/tag/inbox-preview-12 [S: G2]. It brings the troubleshooter's driver page and midiksinfo.
2. **USBView** (Windows SDK debugging tools) or **Thesycon's tdd.exe** (thesycon.de), to read descriptors. Sizes not checked. Reading descriptors queries the KeyLab through the hub, so running it is a separate go from installing it [I].
3. **WinDbg** (Microsoft), to read the two minidumps (`082026-25562-01.dmp`, 16,777,212 bytes; `102126-28718-01.dmp`, 8,923,884 bytes) and name the drivers behind 0x133 and 0x9F. Size not checked.
4. **Specs, as PDFs** (sizes not checked): USB 2.0 (usb.org), USB Device Class Definition for MIDI Devices 1.0 (usb.org), and xHCI 1.2 (Intel).
5. **Books, to buy rather than download:** Windows Internals 7th edition, Part 1, chapter 6; Yosifovich's Windows Kernel Programming, 2nd edition.

## Sources

- **Microsoft Learn (learn.microsoft.com/en-us/windows-hardware/drivers/…), fetched tonight:**
  - L1 Identifier Score
  - L2 Signature Score
  - L4 USB Generic Parent Driver (usbccgp)
  - L5 Enumeration of USB composite devices
  - L6 Driver Signing Policy
  - L7 Loading Test Signed Code
  - L8 PnP Device Installation Signing Requirements
- **Microsoft Learn, cited from standard references and not fetched tonight:**
  - L3 How Windows ranks driver packages
  - L9 Bug Check 0x9F
  - L10 Bug Check 0x133
  - L11 Standard USB identifiers
  - L12 WinUSB and its pipe policies
  - L13 Choosing a driver model and the UMDF architecture
  - L14 IRQLs, ISRs and DPCs
  - L15 What is a driver, device stacks, IRPs
  - L16 Run from driver store and DIRIDs
  - L17 WDDM and TDR
  - L18 Message-signalled interrupts
- **Windows MIDI Services KB (microsoft.github.io/MIDI/kb/…), fetched tonight:**
  - M1 how-to-switch-between-class-drivers
  - M2 kernel-streaming-aggregate
  - M3 virtual-device-app
  - M4 the KB index
- **Other web pages, fetched tonight:**
  - T1 thesycon.de/eng/usb_audiodriver.shtml
  - P1 pci-ids 1022:43fd and 1022:43f5
- **Specifications and books, not fetched:**
  - U1 USB 2.0 Specification, chapters 5, 8 and 9
  - U2 USB Device Class Definition for MIDI Devices 1.0, §4 and Table 4-1
  - U3 USB MIDI 2.0 class definition
  - X1 xHCI 1.2
  - B1 Windows Internals 7th edition, Part 1
  - Z1 libwdi on GitHub (pbatard)
- **Our own documents:**
  - G1 `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-hang-study-2026-10-26.md`
  - G2 `E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\keylab-dev-guidance-and-hang-guide-2026-10-27.md`
  - LED frame builder: `E:\AI-Setup\arsenal\keylab\protocol.py`
