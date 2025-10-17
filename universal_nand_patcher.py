import os
import zlib
import xml.etree.ElementTree as ET
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QListWidget, QListWidgetItem, QTextEdit, QMessageBox, QFrame, QHBoxLayout
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor

XML_FILE = "layout.xml"
PATCHED_DIR = "Patched"

# --- Style Constants ---
DARK_PRIMARY = "#333333"
DARK_SECONDARY = "#444444"
TEXT_COLOR = "#E0E0E0"
ACCENT_COLOR = "#007ACC"  # A modern blue for highlights

class Region:
    def __init__(self, name, address, size):
        self.name = name
        self.address = address
        self.size = size
        self.patch_path = None

class NandPatcherGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Universal NAND Patcher Tool 🛠️")
        self.setFixedSize(500, 600)  # Increased size for better layout
        self.setAcceptDrops(True)
        self.setStyleSheet(self._get_stylesheet())

        self.regions = []
        self.original_bin = None

        self.setup_ui()

    def _get_stylesheet(self):
        # Professional and Modern Dark Theme Stylesheet
        return f"""
            QWidget {{
                background-color: {DARK_PRIMARY};
                color: {TEXT_COLOR};
                font-family: 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif;
                font-size: 10pt;
            }}
            QLabel#InfoLabel {{
                font-size: 11pt;
                font-weight: bold;
                padding: 10px;
                border: 1px dashed {DARK_SECONDARY};
                border-radius: 5px;
                background-color: {DARK_SECONDARY};
                qproperty-alignment: 'AlignCenter';
            }}
            QPushButton {{
                background-color: {ACCENT_COLOR};
                color: white;
                border: 1px solid {ACCENT_COLOR};
                border-radius: 5px;
                padding: 8px 15px;
                min-height: 25px;
            }}
            QPushButton:hover {{
                background-color: #005A99;
                border: 1px solid #005A99;
            }}
            QPushButton:pressed {{
                background-color: #003F6F;
            }}
            QPushButton#ClearButton {{
                background-color: {DARK_SECONDARY};
                border: 1px solid {DARK_SECONDARY};
            }}
            QPushButton#ClearButton:hover {{
                background-color: #666666;
            }}
            QListWidget {{
                background-color: {DARK_SECONDARY};
                border: 1px solid {ACCENT_COLOR};
                border-radius: 5px;
                padding: 5px;
                outline: 0; /* Remove focus border */
            }}
            QListWidget::item:selected {{
                background-color: {ACCENT_COLOR};
                color: white;
            }}
            QTextEdit {{
                background-color: #222222; /* Even darker for log area */
                color: #A0FFA0; /* Light green for log success/info */
                border: 1px solid {DARK_SECONDARY};
                border-radius: 5px;
                padding: 5px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
            }}
        """

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # --- Info/Drop Zone ---
        self.info_label = QLabel("⬇️ Drop NAND .bin or layout .xml file here ⬇️")
        self.info_label.setObjectName("InfoLabel") # Used for CSS targeting
        main_layout.addWidget(self.info_label)

        # --- Region List ---
        list_label = QLabel("Regions:")
        list_label.setFont(QFont(self.font().family(), 10, QFont.Weight.Bold))
        main_layout.addWidget(list_label)

        self.region_list = QListWidget()
        self.region_list.itemChanged.connect(self.auto_select_checked_item)
        self.region_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.region_list.setMinimumHeight(150)
        main_layout.addWidget(self.region_list)

        # --- Action Buttons ---
        button_layout = QHBoxLayout()

        self.select_patch_button = QPushButton("Select Patch File")
        self.select_patch_button.clicked.connect(self.select_patch_file)
        button_layout.addWidget(self.select_patch_button)

        self.build_button = QPushButton("Build Patched Image 💾")
        self.build_button.clicked.connect(self.build_image)
        button_layout.addWidget(self.build_button)

        main_layout.addLayout(button_layout)

        # --- Log Output ---
        log_label = QLabel("Output Log:")
        log_label.setFont(QFont(self.font().family(), 10, QFont.Weight.Bold))
        main_layout.addWidget(log_label)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(150)
        main_layout.addWidget(self.log_output)

        # --- Clear Button (At the bottom) ---
        self.clear_button = QPushButton("Clear")
        self.clear_button.setObjectName("ClearButton")
        self.clear_button.clicked.connect(self.reset_gui)
        main_layout.addWidget(self.clear_button)

    # --- Methods from original code (omitted for brevity, assume they are present) ---
    def auto_select_checked_item(self, item):
        if item.checkState() == Qt.CheckState.Checked:
            item.setSelected(True)

    def reset_gui(self):
        self.region_list.clear()
        self.regions.clear()
        self.original_bin = None
        self.info_label.setText("⬇️ Drop NAND .bin or layout .xml file here ⬇️")
        self.log_output.clear()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".bin"):
                self.original_bin = path
                self.info_label.setText(f"Loaded NAND: {os.path.basename(path)}")
                self.log(f"[✓] .bin file loaded: {path}")
            elif path.lower().endswith(".xml"):
                global XML_FILE
                XML_FILE = path
                self.load_xml_regions()

    def load_xml_regions(self):
        self.region_list.clear()
        self.regions.clear()
        try:
            tree = ET.parse(XML_FILE)
            root = tree.getroot()
            mems = root.find("Memorys")
            if mems is None:
                self.log("[!] <Memorys> tag not found in XML.")
                return
            for mem in mems.findall("Memory"):
                name = mem.findtext("Name", default="Unnamed")
                # Ensure address and size are treated as hexadecimal, but safely
                try:
                    address = int(mem.findtext("Address", "0x0"), 16)
                except ValueError:
                    address = 0
                try:
                    size = int(mem.findtext("Size", "0x0"), 16)
                except ValueError:
                    size = 0
                    
                region = Region(name, address, size)
                self.regions.append(region)
                # Display more clearly, use monospace font in item for alignment
                display_text = f"{name:<15} @ 0x{address:08X} | Size: 0x{size:X}"
                item = QListWidgetItem(display_text)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.region_list.addItem(item)
            self.log(f"[✓] layout.xml loaded: {XML_FILE}")
        except Exception as e:
            self.log(f"[!] Failed to parse XML: {e}")

    def select_patch_file(self):
        for idx in range(self.region_list.count()):
            item = self.region_list.item(idx)
            # Only proceed if the item is both selected AND checked
            if item.isSelected() and item.checkState() == Qt.CheckState.Checked:
                region = self.regions[idx]
                # Default filter to *.bin
                path, _ = QFileDialog.getOpenFileName(self, f"Select Patch for {region.name}", "", "Binary Files (*.bin);;All Files (*)")
                if path:
                    region.patch_path = path
                    # Update the list item text to show the patch path
                    original_text = item.text().split(' -> ')[0] # Remove old path if exists
                    item.setText(f"{original_text} -> {os.path.basename(path)}")
                    self.log(f"[✓] Patch selected for {region.name}: {os.path.basename(path)}")
                return
        self.log("[!] Please check and select a region before assigning a patch.")

    def build_image(self):
        if not self.original_bin:
            self.log("[!] No original .bin file loaded. Aborting build.")
            return

        try:
            with open(self.original_bin, "rb") as f:
                full_image = bytearray(f.read())
        except Exception as e:
            self.log(f"[!] Failed to read .bin file: {e}")
            return

        os.makedirs(PATCHED_DIR, exist_ok=True)
        # Use an f-string to ensure the patched filename is distinct, e.g., "original_patched.bin"
        base_name = os.path.basename(self.original_bin)
        name, ext = os.path.splitext(base_name)
        patched_filename = f"{name}_patched{ext}"
        patched_path = os.path.join(PATCHED_DIR, patched_filename)
        log_path = os.path.join(PATCHED_DIR, "patched_log.txt")

        patches_applied = False
        self.log("\n--- Starting Patch Process ---")

        with open(log_path, "w") as log_file:
            log_file.write(f"Patched Log for {patched_path}\nOriginal File: {self.original_bin}\nLayout: {XML_FILE}\n\n")
            log_file.write(f"{'Region':<15} | {'CRC32':<8} | {'CHKSUM':<8} | {'Status'}\n")
            log_file.write("-" * 50 + "\n")

            for idx, region in enumerate(self.regions):
                item = self.region_list.item(idx)
                if item.checkState() == Qt.CheckState.Checked and region.patch_path:
                    try:
                        with open(region.patch_path, "rb") as pf:
                            patch_data = pf.read()

                        patch_status = "OK"

                        # Handle size mismatch
                        if len(patch_data) != region.size:
                            patch_status = "SIZE_MISMATCH"
                            # Use critical icon for a clearer message
                            result = QMessageBox.critical(
                                self, "Size Mismatch Warning",
                                f"Patch for **{region.name}** is **{len(patch_data)}** bytes, expected **{region.size}**.\n\n"
                                f"Do you want to **TRUNCATE/PAD** the patch data to fit the region size (0x{region.size:X})?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                QMessageBox.StandardButton.Yes
                            )
                            if result == QMessageBox.StandardButton.No:
                                self.log(f"[!] Skipped {region.name} - Size mismatch unhandled.")
                                log_file.write(f"{region.name:<15} | {'-'*8} | {'-'*8} | SKIPPED (Size mismatch)\n")
                                continue
                            
                            # Truncate or Pad with 0xFF (common for erased flash blocks)
                            patch_data = patch_data[:region.size] + bytes([0xFF] * max(0, region.size - len(patch_data)))

                        # Apply patch to the image
                        if region.address + region.size > len(full_image):
                            self.log(f"[!] ERROR: Region {region.name} extends beyond image size. Skipping.")
                            log_file.write(f"{region.name:<15} | {'-'*8} | {'-'*8} | ERROR (Out of bounds)\n")
                            continue

                        full_image[region.address:region.address + region.size] = patch_data
                        patches_applied = True

                        # Calculate Checksums
                        crc = zlib.crc32(patch_data) & 0xFFFFFFFF
                        checksum = sum(patch_data) & 0xFFFFFFFF # Simple additive checksum

                        self.log(f"[+] Patched {region.name:<15} | CRC32: {crc:08X} | CHKSUM: {checksum:08X}")
                        log_file.write(f"{region.name:<15} | {crc:08X} | {checksum:08X} | {patch_status}\n")

                    except Exception as e:
                        self.log(f"[!] Failed patching {region.name}: {e}")
                        log_file.write(f"{region.name:<15} | {'-'*8} | {'-'*8} | ERROR ({str(e).replace('\n', ' ')[:20]}...)\n")

            if not patches_applied:
                self.log("\n[i] No patches were applied. The output file will be a copy of the original.")
            
            log_file.write("\n--- Final Image Status ---\n")

        # --- Final Image Save and Checksums ---
        try:
            with open(patched_path, "wb") as out:
                out.write(full_image)

            # Recalculate full image checksums
            final_crc = zlib.crc32(full_image) & 0xFFFFFFFF
            final_checksum = sum(full_image) & 0xFFFFFFFF
            
            # Read original file again for comparison
            with open(self.original_bin, "rb") as f:
                original_data = f.read()
            orig_crc = zlib.crc32(original_data) & 0xFFFFFFFF
            orig_checksum = sum(original_data) & 0xFFFFFFFF

            self.log(f"\n[✔️] **Patched image saved to:** {patched_path}")
            self.log(f"[i] **Final Image CRC32** : {final_crc:08X}")
            self.log(f"[i] **Final Image CHKSUM**: {final_checksum:08X}")
            self.log(f"[i] **Original CRC32** : {orig_crc:08X}")
            self.log(f"[i] **Original CHKSUM** : {orig_checksum:08X}")

            if final_crc == orig_crc and final_checksum == orig_checksum and patches_applied:
                 self.log("[⚠️] **Image integrity Warning:** Final image checksums match the original, but patches were applied. Verify patch application!")
            elif final_crc != orig_crc or final_checksum != orig_checksum:
                self.log("[✔️] **Image integrity Check:** CRC/CHKSUM changed (as expected).")
            else:
                self.log("[i] **Image integrity Check:** No patches applied, checksums match.")

            # Append final results to log file
            with open(log_path, "a") as log_file:
                 log_file.write(f"Original CRC32: {orig_crc:08X}\n")
                 log_file.write(f"Original CHKSUM: {orig_checksum:08X}\n")
                 log_file.write(f"Patched CRC32: {final_crc:08X}\n")
                 log_file.write(f"Patched CHKSUM: {final_checksum:08X}\n")
                 log_file.write(f"\nPatched image saved successfully to: {patched_path}\n")

        except Exception as e:
            self.log(f"[!] **Failed to write patched image:** {e}")

    def log(self, msg):
        self.log_output.append(msg)
# --- End of Methods ---


if __name__ == '__main__':
    # Set the application's style for better native look/feel (optional, but good practice)
    # Note: Stylesheet overrides most of this, but it can set global defaults.
    # On some systems, setting the style to 'Fusion' works well with custom stylesheets.
    # app = QApplication([])
    # app.setStyle("Fusion") 
    
    app = QApplication([])
    window = NandPatcherGUI()
    window.show()
    app.exec()
