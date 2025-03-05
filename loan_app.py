# create a folder naming LoanApp ad add the file with the code

import sys
import sqlite3
from PyQt5 import QtWidgets, QtCore, QtGui

class LoanApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_db()
        self.init_ui()
        
    def init_db(self):
        self.conn = sqlite3.connect('loans.db')
        self.c = self.conn.cursor()
        
        # Create tables
        self.c.execute('''CREATE TABLE IF NOT EXISTS Customers (
                         ID INTEGER PRIMARY KEY,
                         Name TEXT NOT NULL,
                         Phone TEXT NOT NULL,
                         MaterialType TEXT CHECK(MaterialType IN ('Gold', 'Silver')),
                         ItemName TEXT,
                         EntryDate DATETIME DEFAULT CURRENT_TIMESTAMP,
                         ExitDate DATETIME,
                         PrincipalAmount REAL,
                         InterestRate REAL,
                         Status TEXT CHECK(Status IN ('Active', 'Returned')))''')
        
        self.c.execute('''CREATE TABLE IF NOT EXISTS Settings (
                         Key TEXT PRIMARY KEY,
                         Value TEXT)''')
        
        # Set default interest rate
        self.c.execute('''INSERT OR IGNORE INTO Settings (Key, Value) 
                         VALUES ('DailyInterestRate', '0.1')''')
        self.conn.commit()
        
        # Auto-delete old records
        self.c.execute('''DELETE FROM Customers 
                          WHERE Status = 'Returned' AND 
                          ExitDate < datetime('now', '-3 months')''')
        self.conn.commit()

    def init_ui(self):
        self.setWindowTitle('Gold/Silver Loan Management')
        self.setGeometry(100, 100, 1000, 700)
        
        # Main Table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(['ID', 'Name', 'Phone', 'Material', 'Item', 
                                             'Entry Date', 'Status', 'Days Held', 'Interest Owed'])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        
        # Search
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Search by name, phone, or item...")
        self.search_box.textChanged.connect(self.update_table)
        
        # Buttons
        self.add_btn = QtWidgets.QPushButton('Add New Loan')
        self.return_btn = QtWidgets.QPushButton('Mark Returned')
        self.settings_btn = QtWidgets.QPushButton('Interest Settings')
        
        # Layout
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.search_box)
        main_layout.addWidget(self.table)
        
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.add_btn)
        button_layout.addWidget(self.return_btn)
        button_layout.addWidget(self.settings_btn)
        
        main_layout.addLayout(button_layout)
        
        container = QtWidgets.QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        
        # Connect buttons
        self.add_btn.clicked.connect(self.show_add_dialog)
        self.return_btn.clicked.connect(self.mark_returned)
        self.settings_btn.clicked.connect(self.show_settings)
        
        self.update_table()
        self.check_alerts()

    def update_table(self):
        search_text = self.search_box.text()
        query = '''
            SELECT 
                ID, 
                Name, 
                Phone, 
                MaterialType, 
                ItemName, 
                strftime('%d-%m-%Y', EntryDate),
                Status,
                (JULIANDAY(COALESCE(ExitDate, datetime('now'))) - JULIANDAY(EntryDate)),
                ROUND(
                    PrincipalAmount * 
                    (JULIANDAY(COALESCE(ExitDate, datetime('now'))) - JULIANDAY(EntryDate)) *
                    (SELECT Value FROM Settings WHERE Key = 'DailyInterestRate') / 100,
                    2
                )
            FROM Customers 
            WHERE 
                Name LIKE ? OR 
                Phone LIKE ? OR 
                ItemName LIKE ?'''
        
        self.c.execute(query, (f'%{search_text}%', f'%{search_text}%', f'%{search_text}%'))
        data = self.c.fetchall()
        
        self.table.setRowCount(len(data))
        for row, record in enumerate(data):
            for col, value in enumerate(record):
                item = QtWidgets.QTableWidgetItem(str(value))
                if col == 7:  # Days Held column
                    bg_color = QtGui.QColor(255, 200, 200) if int(value) > 365 else QtGui.QColor(255, 255, 255)
                    item.setBackground(bg_color)
                self.table.setItem(row, col, item)

    def show_add_dialog(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Add New Loan")
        dialog.setFixedSize(400, 300)
        
        form = QtWidgets.QFormLayout()
        
        # Input fields
        name_input = QtWidgets.QLineEdit()
        phone_input = QtWidgets.QLineEdit()
        material_combo = QtWidgets.QComboBox()
        material_combo.addItems(['Gold', 'Silver'])
        item_input = QtWidgets.QLineEdit()
        principal_spin = QtWidgets.QDoubleSpinBox()
        principal_spin.setRange(100, 1000000)
        principal_spin.setPrefix("₹ ")
        
        # Buttons
        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        
        # Add to layout
        form.addRow("Customer Name:", name_input)
        form.addRow("Phone Number:", phone_input)
        form.addRow("Material Type:", material_combo)
        form.addRow("Item Name:", item_input)
        form.addRow("Loan Amount:", principal_spin)
        form.addRow(btn_box)
        
        dialog.setLayout(form)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            self.c.execute('''INSERT INTO Customers 
                           (Name, Phone, MaterialType, ItemName, PrincipalAmount, Status)
                           VALUES (?, ?, ?, ?, ?, 'Active')''',
                           (name_input.text(), 
                            phone_input.text(),
                            material_combo.currentText(),
                            item_input.text(),
                            principal_spin.value()))
            self.conn.commit()
            self.update_table()

    def mark_returned(self):
        selected_row = self.table.currentRow()
        if selected_row >= 0:
            loan_id = self.table.item(selected_row, 0).text()
            self.c.execute('''UPDATE Customers 
                             SET Status = 'Returned', 
                             ExitDate = CURRENT_TIMESTAMP 
                             WHERE ID = ?''', (loan_id,))
            self.conn.commit()
            self.update_table()

    def show_settings(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Interest Settings")
        
        layout = QtWidgets.QVBoxLayout()
        
        # Interest Rate Input
        rate_input = QtWidgets.QDoubleSpinBox()
        rate_input.setDecimals(3)
        rate_input.setRange(0.001, 10.0)
        rate_input.setSuffix("%")
        
        # Load current rate
        self.c.execute('SELECT Value FROM Settings WHERE Key = "DailyInterestRate"')
        current_rate = float(self.c.fetchone()[0])
        rate_input.setValue(current_rate)
        
        # Save Button
        save_btn = QtWidgets.QPushButton("Save")
        save_btn.clicked.connect(lambda: self.save_settings(rate_input.value(), dialog))
        
        layout.addWidget(QtWidgets.QLabel("Daily Interest Rate:"))
        layout.addWidget(rate_input)
        layout.addWidget(save_btn)
        dialog.setLayout(layout)
        dialog.exec_()

    def save_settings(self, new_rate, dialog):
        self.c.execute('''UPDATE Settings 
                          SET Value = ? 
                          WHERE Key = 'DailyInterestRate' ''', (str(new_rate),))
        self.conn.commit()
        dialog.close()
        self.update_table()

    def check_alerts(self):
        self.c.execute('''SELECT Name, ItemName, EntryDate FROM Customers 
                        WHERE Status = 'Active' AND 
                        DATE(EntryDate) < DATE('now', '-1 year')''')
        alerts = self.c.fetchall()
        
        if alerts:
            alert_text = "Items held over 1 year:\n\n"
            for name, item, entry_date in alerts:
                alert_text += f"• {name} - {item} (since {entry_date})\n"
            
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setText(alert_text)
            msg.setWindowTitle("Overdue Alert")
            msg.exec_()

    def closeEvent(self, event):
        self.conn.close()
        event.accept()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = LoanApp()
    window.show()
    sys.exit(app.exec_())
