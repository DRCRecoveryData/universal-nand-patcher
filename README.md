# Universal NAND Patcher Tool

<img width="502" height="632" alt="image" src="https://github.com/user-attachments/assets/459f5caf-078a-401f-912d-1eed6a76abd9" />

A drag-and-drop PyQt6 GUI for patching NAND `.bin` images using region definitions in a `layout.xml` file.

---

## 🚀 Features

- ✅ Drop `.bin` NAND images and `.xml` layout files directly into the GUI.
- ✅ Automatically parses regions from XML.
- ✅ Check/select memory regions to patch with custom `.bin` files.
- ✅ Handles size mismatches with padding/truncation options.
- ✅ Logs all actions to `patched_log.txt`.
- ✅ Shows both **CRC32** and **Checksum** for each region and final image.

---

## 📦 Requirements

- Python 3.8+
- PyQt6

Install dependencies:
```bash
pip install -r requirements.txt
````

---

## 💡 How to Use

1. **Run the GUI**:

```bash
python universal_nand_patcher.py
```

2. **Drag & Drop** your `.bin` NAND file into the window.
3. **Drag & Drop** the `layout.xml` file.
4. Check the regions you want to patch.
5. Click **"Select Patch File"** and choose `.bin` patch files.
6. Click **"Build Patched Image"**.
7. Done! The result is saved in the `Patched/` folder.

---

## 📁 Example XML Layout

```xml
<Root>
  <Memorys>
    <Memory>
      <Name>Bootloader</Name>
      <Address>0x000000</Address>
      <Size>0x20000</Size>
    </Memory>
    <Memory>
      <Name>Kernel</Name>
      <Address>0x20000</Address>
      <Size>0x400000</Size>
    </Memory>
  </Memorys>
</Root>
```

---

## 📂 Output

After patching:

* `Patched/yourfile.bin` → the fully patched NAND image.
* `Patched/patched_log.txt` → log of all patched regions, CRC32 and checksums.

---

## 📜 License

This project is licensed under the **MIT License**.
