import os
import zlib
import xml.etree.ElementTree as ET
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QListWidget, QListWidgetItem, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt

XML_FILE = "layout.xml"
EXTRACT_DIR = "Extracted"
PATCHED_DIR = "Patched"

class Region:
    def __init__(self, name, address, size):
        self.name = name
        self.address = address
        self.size = size
        self.patch_path = None

class NandPatcherGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Universal NAND Patcher Tool")
        self.setFixedSize(400, 400)
        self.setAcceptDrops(True)
        self.regions = []
        self.original_bin = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.info_label = QLabel("Drop NAND .bin or layout .xml file here")
        self.layout.addWidget(self.info_label)

        self.region_list = QListWidget()
        self.region_list.itemChanged.connect(self.auto_select_checked_item)
        self.layout.addWidget(self.region_list)

        self.select_patch_button = QPushButton("Select Patch File for Selected Region")
        self.select_patch_button.clicked.connect(self.select_patch_file)
        self.layout.addWidget(self.select_patch_button)

        self.build_button = QPushButton("Build Patched Image")
        self.build_button.clicked.connect(self.build_image)
        self.layout.addWidget(self.build_button)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.layout.addWidget(self.log_output)

    def auto_select_checked_item(self, item):
        if item.checkState() == Qt.CheckState.Checked:
            item.setSelected(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".bin"):
                self.original_bin = path
                self.info_label.setText(f"Loaded: {os.path.basename(self.original_bin)}")
                self.log(f"[✓] .bin file loaded: {self.original_bin}")
            elif path.lower().endswith(".xml"):
                global XML_FILE
                XML_FILE = path
                self.region_list.clear()
                self.regions.clear()
                self.load_xml_regions()
                self.log(f"[✓] layout.xml loaded: {XML_FILE}")

    def load_xml_regions(self):
        try:
            tree = ET.parse(XML_FILE)
            root = tree.getroot()
            for mem in root.find("Memorys").findall("Memory"):
                name = mem.findtext("Name")
                address = int(mem.findtext("Address"), 16)
                size = int(mem.findtext("Size"), 16)
                region = Region(name, address, size)
                self.regions.append(region)
                item = QListWidgetItem(f"{name} @ 0x{address:X} size: 0x{size:X}")
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.region_list.addItem(item)
        except Exception as e:
            self.log(f"[!] Failed to parse XML: {e}")

    def select_patch_file(self):
        for idx in range(self.region_list.count()):
            item = self.region_list.item(idx)
            if item.isSelected() and item.checkState() == Qt.CheckState.Checked:
                region = self.regions[idx]
                path, _ = QFileDialog.getOpenFileName(self, "Select Patch File", "", "Binary Files (*.bin)")
                if path:
                    region.patch_path = path
                    self.log(f"[✓] Patch selected for {region.name}: {path}")
                return
        self.log("[!] Please check and select a region before assigning a patch.")

    def build_image(self):
        if not self.original_bin:
            self.log("[!] No original .bin file loaded.")
            return

        with open(self.original_bin, "rb") as f:
            full_image = bytearray(f.read())

        os.makedirs(PATCHED_DIR, exist_ok=True)
        patched_path = os.path.join(PATCHED_DIR, os.path.basename(self.original_bin))
        log_path = os.path.join(PATCHED_DIR, "patched_log.txt")

        with open(log_path, "w") as log_file:
            log_file.write(f"Patched Log for {patched_path}\n\n")

            for idx, region in enumerate(self.regions):
                item = self.region_list.item(idx)
                if item.checkState() == Qt.CheckState.Checked and region.patch_path:
                    with open(region.patch_path, "rb") as pf:
                        patch_data = pf.read()

                    if len(patch_data) != region.size:
                        result = QMessageBox.question(self, "Size Mismatch",
                            f"Patch for {region.name} is {len(patch_data)} bytes, expected {region.size}.\nTruncate or pad?",
                            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                        if result == QMessageBox.StandardButton.No:
                            self.log(f"[!] Skipped {region.name}")
                            continue
                        patch_data = patch_data[:region.size] + bytes([0xFF] * max(0, region.size - len(patch_data)))

                    full_image[region.address:region.address + region.size] = patch_data

                    crc = zlib.crc32(patch_data) & 0xFFFFFFFF
                    checksum = sum(patch_data) & 0xFFFFFFFF

                    self.log(f"[+] Patched {region.name:<15} | CRC32: {crc:08X} | CHKSUM: {checksum:08X}")
                    log_file.write(f"{region.name:<15} | CRC32: {crc:08X} | CHKSUM: {checksum:08X}\n")

            with open(patched_path, "wb") as out:
                out.write(full_image)

            final_crc = zlib.crc32(full_image) & 0xFFFFFFFF
            final_checksum = sum(full_image) & 0xFFFFFFFF
            orig_crc = zlib.crc32(open(self.original_bin, "rb").read()) & 0xFFFFFFFF
            orig_checksum = sum(open(self.original_bin, "rb").read()) & 0xFFFFFFFF

            self.log(f"\n[✓] Patched image saved to: {patched_path}")
            self.log(f"[✓] Final CRC32   : {final_crc:08X}")
            self.log(f"[✓] Final CHKSUM : {final_checksum:08X}")
            self.log(f"[i]  Original CRC32   : {orig_crc:08X}")
            self.log(f"[i]  Original CHKSUM  : {orig_checksum:08X}")
            if final_crc == orig_crc and final_checksum == orig_checksum:
                self.log("[✓] Image integrity: CRC + CHKSUM MATCH")
            else:
                self.log("[!] Image integrity: CRC or CHKSUM MISMATCH")

    def log(self, msg):
        self.log_output.append(msg)

if __name__ == '__main__':
    app = QApplication([])
    window = NandPatcherGUI()
    window.show()
    app.exec()
