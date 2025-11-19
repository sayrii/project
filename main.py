import csv
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QAbstractTableModel
from PyQt6.QtGui import QAction, QFont, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QMenu, QMenuBar,
    QPushButton, QScrollArea, QStatusBar, QTableView, QVBoxLayout, QWidget
)


@dataclass
class Dish:
    id: int
    name: str
    price: float
    image_path: str
    selected: bool = False


class DatabaseManager:
    def __init__(self, db_name="dishes.db"):
        self.db_name = db_name
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        tables = [
            '''CREATE TABLE IF NOT EXISTS dishes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                image_path TEXT NOT NULL)''',
            '''CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_amount REAL NOT NULL,
                order_date TEXT NOT NULL)''',
            '''CREATE TABLE IF NOT EXISTS order_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                dish_id INTEGER,
                quantity INTEGER,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (dish_id) REFERENCES dishes (id))'''
        ]

        for table in tables:
            cursor.execute(table)

        cursor.execute("SELECT COUNT(*) FROM dishes")
        if cursor.fetchone()[0] == 0:
            sample_dishes = [
                ("Паста Карбонара", 12.99, "images/pasta.jpg"),
                ("Пицца Маргарита", 15.50, "images/pizza.jpg"),
                ("Салат Цезарь", 8.75, "images/salad.jpg"),
                ("Стейк Рибай", 25.99, "images/steak.jpg"),
                ("Суши Калифорния", 18.25, "images/sushi.jpg"),
                ("Борщ", 7.50, "images/borscht.jpg"),
                ("Пельмени", 10.25, "images/dumplings.jpg")
            ]
            cursor.executemany(
                "INSERT INTO dishes (name, price, image_path) VALUES (?, ?, ?)",
                sample_dishes
            )

        conn.commit()
        conn.close()

    def get_all_dishes(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price, image_path FROM dishes")
        dishes = [Dish(*row) for row in cursor.fetchall()]
        conn.close()
        return dishes

    def save_order(self, selected_dishes, total_amount):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        order_date = datetime.now().isoformat()

        cursor.execute(
            "INSERT INTO orders (total_amount, order_date) VALUES (?, ?)",
            (total_amount, order_date)
        )
        order_id = cursor.lastrowid

        for dish in selected_dishes:
            cursor.execute(
                "INSERT INTO order_details (order_id, dish_id, quantity) "
                "VALUES (?, ?, ?)",
                (order_id, dish.id, 1)
            )

        conn.commit()
        conn.close()
        return order_id

    def get_order_history(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT o.id, o.total_amount, o.order_date,
                   GROUP_CONCAT(d.name, ', ') as dish_names
            FROM orders o
            LEFT JOIN order_details od ON o.id = od.order_id
            LEFT JOIN dishes d ON od.dish_id = d.id
            GROUP BY o.id
            ORDER BY o.order_date DESC
        ''')
        orders = cursor.fetchall()
        conn.close()
        return orders

    def add_new_dish(self, name, price, image_path):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO dishes (name, price, image_path) VALUES (?, ?, ?)",
            (name, price, image_path)
        )
        dish_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return dish_id

    def delete_dish(self, dish_id):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dishes WHERE id = ?", (dish_id,))
        conn.commit()
        conn.close()


class OrdersTableModel(QAbstractTableModel):
    def __init__(self, orders):
        super().__init__()
        self.orders = orders
        self.headers = ["ID", "Сумма", "Дата", "Блюда"]

    def rowCount(self, parent=None):
        return len(self.orders)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole:
            order = self.orders[index.row()]
            if index.column() == 1:
                return f"{order[index.column()]:.2f} ₽"
            return str(order[index.column()])
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if (role == Qt.ItemDataRole.DisplayRole
                and orientation == Qt.Orientation.Horizontal):
            return self.headers[section]
        return None


class DishWidget(QWidget):
    def __init__(self, dish, on_selection_change):
        super().__init__()
        self.dish = dish
        self.on_selection_change = on_selection_change
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        layout.setSpacing(10)

        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(self.on_checkbox_changed)
        layout.addWidget(self.checkbox)

        self.load_image(layout)

        name_label = QLabel(self.dish.name)
        name_label.setFont(QFont("Arial", 12))
        layout.addWidget(name_label)

        layout.addStretch()

        price_label = QLabel(f"{self.dish.price:.2f} ₽")
        price_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        price_label.setStyleSheet("color: #e74c3c;")
        layout.addWidget(price_label)

        self.setLayout(layout)
        self.setFixedHeight(100)
        self.setStyleSheet("""
            DishWidget {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px;
                background: white;
            }
        """)

    def load_image(self, layout):
        try:
            pixmap = QPixmap(self.dish.image_path)
            if pixmap.isNull():
                raise Exception("Image not found")

            image_label = QLabel()
            image_label.setPixmap(pixmap.scaled(
                80, 80, Qt.AspectRatioMode.KeepAspectRatio
            ))
            layout.addWidget(image_label)
        except Exception:
            error_label = QLabel("Нет изображения")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet("color: #999;")
            layout.addWidget(error_label)

    def on_checkbox_changed(self, state):
        self.dish.selected = (state == Qt.CheckState.Checked.value)
        self.on_selection_change()


class AddDishDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_image_path = ""
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        self.setWindowTitle("Добавить новое блюдо")
        self.resize(500, 300)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Введите название блюда")
        form_layout.addRow("Название:", self.name_input)

        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0.01, 1000.0)
        self.price_input.setDecimals(2)
        self.price_input.setSuffix(" ₽")
        self.price_input.setValue(10.0)
        form_layout.addRow("Цена:", self.price_input)

        image_layout = QHBoxLayout()
        self.image_input = QLineEdit()
        self.image_input.setPlaceholderText("Выберите изображение...")
        self.image_input.setReadOnly(True)
        image_layout.addWidget(self.image_input)

        self.select_image_btn = QPushButton("Выбрать")
        image_layout.addWidget(self.select_image_btn)
        form_layout.addRow("Изображение:", image_layout)

        self.image_preview = QLabel()
        self.image_preview.setFixedSize(100, 100)
        self.image_preview.setStyleSheet(
            "border: 2px dashed #ccc; background-color: #f9f9f9;"
        )
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setText("Превью изображения")
        form_layout.addRow("Превью:", self.image_preview)

        layout.addLayout(form_layout)

        buttons_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Отмена")
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addStretch()

        self.add_btn = QPushButton("Добавить блюдо")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ecc71;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #27ae60;
            }
        """)
        buttons_layout.addWidget(self.add_btn)
        layout.addLayout(buttons_layout)

    def setup_connections(self):
        self.cancel_btn.clicked.connect(self.reject)
        self.add_btn.clicked.connect(self.accept)
        self.select_image_btn.clicked.connect(self.select_image)

    def select_image(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Выберите изображение блюда", "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All files (*.*)"
        )

        if filename:
            self.selected_image_path = filename
            self.image_input.setText(filename)
            pixmap = QPixmap(filename)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    96, 96, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_preview.setPixmap(scaled_pixmap)
            else:
                self.image_preview.setText("Ошибка загрузки")

    def get_dish_data(self):
        image_path = self.copy_image_to_folder()
        return {
            'name': self.name_input.text().strip(),
            'price': self.price_input.value(),
            'image_path': image_path
        }

    def copy_image_to_folder(self):
        if not self.selected_image_path:
            return "images/default.jpg"

        try:
            import os
            if not os.path.exists("images"):
                os.makedirs("images")

            name = self.name_input.text().strip() or "new_dish"
            safe_name = "".join(c if c.isalnum() else "_" for c in name)

            import os.path
            extension = os.path.splitext(self.selected_image_path)[1] or ".jpg"
            new_filename = f"images/{safe_name}{extension}"

            shutil.copy2(self.selected_image_path, new_filename)
            return new_filename

        except Exception as e:
            print(f"Ошибка копирования изображения: {e}")
            return "images/default.jpg"


class DeleteDishDialog(QDialog):
    def __init__(self, dishes, parent=None):
        super().__init__(parent)
        self.dishes = dishes
        self.selected_dish_id = None
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        self.setWindowTitle("Удалить блюдо")
        self.resize(400, 300)

        layout = QVBoxLayout(self)
        title_label = QLabel("Выберите блюдо для удаления:")
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)

        self.dishes_list = QListWidget()
        for dish in self.dishes:
            item_text = f"{dish.name} - {dish.price:.2f} ₽"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, dish.id)
            self.dishes_list.addItem(item)
        layout.addWidget(self.dishes_list)

        buttons_layout = QHBoxLayout()
        self.cancel_btn = QPushButton("Отмена")
        buttons_layout.addWidget(self.cancel_btn)
        buttons_layout.addStretch()

        self.delete_btn = QPushButton("Удалить выбранное")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.delete_btn.setEnabled(False)
        buttons_layout.addWidget(self.delete_btn)
        layout.addLayout(buttons_layout)

    def setup_connections(self):
        self.cancel_btn.clicked.connect(self.reject)
        self.delete_btn.clicked.connect(self.accept)
        self.dishes_list.itemSelectionChanged.connect(self.on_selection_changed)

    def on_selection_changed(self):
        has_selection = len(self.dishes_list.selectedItems()) > 0
        self.delete_btn.setEnabled(has_selection)
        if has_selection:
            selected_item = self.dishes_list.selectedItems()[0]
            self.selected_dish_id = selected_item.data(Qt.ItemDataRole.UserRole)

    def get_selected_dish_id(self):
        return self.selected_dish_id


class OrderHistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.init_ui()
        self.setup_connections()
        self.load_orders()

    def init_ui(self):
        self.setWindowTitle("История заказов")
        self.resize(700, 400)

        layout = QVBoxLayout(self)
        self.orders_table = QTableView()
        layout.addWidget(self.orders_table)

        buttons_layout = QHBoxLayout()
        self.close_btn = QPushButton("Закрыть")
        buttons_layout.addWidget(self.close_btn)
        buttons_layout.addStretch()
        self.export_csv_btn = QPushButton("Экспорт CSV")
        buttons_layout.addWidget(self.export_csv_btn)
        layout.addLayout(buttons_layout)

    def setup_connections(self):
        self.close_btn.clicked.connect(self.close)
        self.export_csv_btn.clicked.connect(self.export_to_csv)

    def load_orders(self):
        orders = self.db_manager.get_order_history()
        model = OrdersTableModel(orders)
        self.orders_table.setModel(model)
        self.orders_table.resizeColumnsToContents()

    def export_to_csv(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Экспорт CSV", "orders.csv", "CSV Files (*.csv)"
        )
        if filename:
            orders = self.db_manager.get_order_history()
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['ID', 'Сумма', 'Дата', 'Блюда'])
                writer.writerows(orders)
            QMessageBox.information(self, "Успех", "Данные экспортированы")


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(900, 700)
        self.centralwidget = QtWidgets.QWidget(parent=MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")

        self.titleLabel = QtWidgets.QLabel(parent=self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.titleLabel.setFont(font)
        self.titleLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.titleLabel.setObjectName("titleLabel")
        self.verticalLayout.addWidget(self.titleLabel)

        self.scrollArea = QtWidgets.QScrollArea(parent=self.centralwidget)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 880, 500))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")

        self.dishesGridLayout = QtWidgets.QGridLayout(self.scrollAreaWidgetContents)
        self.dishesGridLayout.setObjectName("dishesGridLayout")
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout.addWidget(self.scrollArea)

        self.bottomLayout = QtWidgets.QHBoxLayout()
        self.bottomLayout.setObjectName("bottomLayout")

        self.totalGroupBox = QtWidgets.QGroupBox(parent=self.centralwidget)
        self.totalGroupBox.setObjectName("totalGroupBox")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.totalGroupBox)

        self.totalLabel = QtWidgets.QLabel(parent=self.totalGroupBox)
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.totalLabel.setFont(font)
        self.totalLabel.setText("0.00 ₽")
        self.horizontalLayout.addWidget(self.totalLabel)

        self.bottomLayout.addWidget(self.totalGroupBox)
        self.bottomLayout.addStretch()

        self.confirmButton = QtWidgets.QPushButton(parent=self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.confirmButton.setFont(font)
        self.confirmButton.setObjectName("confirmButton")
        self.bottomLayout.addWidget(self.confirmButton)

        self.verticalLayout.addLayout(self.bottomLayout)
        MainWindow.setCentralWidget(self.centralwidget)

        self.menubar = QtWidgets.QMenuBar(parent=MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 900, 28))
        self.menubar.setObjectName("menubar")

        self.menu = QtWidgets.QMenu(parent=self.menubar)
        self.menu.setObjectName("menu")

        actions = [
            ("actionExport", "Экспорт заказа"),
            ("actionViewOrders", "Просмотр заказов"),
            ("actionAddDish", "Добавить блюдо"),
            ("actionDeleteDish", "Удалить блюдо")
        ]

        for action_name, action_text in actions:
            action = QtGui.QAction(parent=MainWindow)
            action.setObjectName(action_name)
            setattr(self, action_name, action)
            self.menu.addAction(action)

        self.menubar.addAction(self.menu.menuAction())
        MainWindow.setMenuBar(self.menubar)

        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Ресторан - Выбор блюд"))
        self.titleLabel.setText(_translate("MainWindow", "Выберите блюда"))
        self.totalGroupBox.setTitle(_translate("MainWindow", "Итого"))
        self.confirmButton.setText(_translate("MainWindow", "Подтвердить заказ"))
        self.menu.setTitle(_translate("MainWindow", "Меню"))
        self.actionExport.setText(_translate("MainWindow", "Экспорт заказа"))
        self.actionViewOrders.setText(_translate("MainWindow", "Просмотр заказов"))
        self.actionAddDish.setText(_translate("MainWindow", "Добавить блюдо"))
        self.actionDeleteDish.setText(_translate("MainWindow", "Удалить блюдо"))


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.db_manager = DatabaseManager()
        self.dishes = []
        self.selected_dishes = []

        self.setup_connections()
        self.load_dishes()
        self.update_total()

    def setup_connections(self):
        self.confirmButton.clicked.connect(self.confirm_order)
        self.actionExport.triggered.connect(self.export_order_txt)
        self.actionViewOrders.triggered.connect(self.show_order_history)
        self.actionAddDish.triggered.connect(self.show_add_dish_dialog)
        self.actionDeleteDish.triggered.connect(self.show_delete_dish_dialog)

    def load_dishes(self):
        self.dishes = self.db_manager.get_all_dishes()
        grid_layout = self.dishesGridLayout

        while grid_layout.count():
            child = grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        row, col = 0, 0
        for dish in self.dishes:
            dish_widget = DishWidget(dish, self.update_total)
            grid_layout.addWidget(dish_widget, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1

    def update_total(self):
        self.selected_dishes = [dish for dish in self.dishes if dish.selected]
        total = sum(dish.price for dish in self.selected_dishes)
        self.totalLabel.setText(f"{total:.2f} ₽")
        self.statusbar.showMessage(f"Выбрано {len(self.selected_dishes)} блюд")

    def confirm_order(self):
        if not self.selected_dishes:
            QMessageBox.warning(self, "Внимание", "Выберите блюда!")
            return

        total = sum(dish.price for dish in self.selected_dishes)
        order_id = self.db_manager.save_order(self.selected_dishes, total)

        QMessageBox.information(
            self, "Успех", f"Заказ #{order_id} сохранен!\nСумма: {total:.2f} ₽"
        )

        for dish in self.dishes:
            dish.selected = False
        self.update_total()
        self.reset_checkboxes()

    def reset_checkboxes(self):
        for i in range(self.dishesGridLayout.count()):
            widget = self.dishesGridLayout.itemAt(i).widget()
            if isinstance(widget, DishWidget):
                widget.checkbox.setChecked(False)

    def export_order_txt(self):
        if not self.selected_dishes:
            QMessageBox.warning(self, "Внимание", "Нет выбранных блюд!")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Экспорт заказа", "order.txt", "Text Files (*.txt)"
        )
        if filename:
            with open(filename, 'w', encoding='utf-8') as file:
                file.write("ВАШ ЗАКАЗ:\n")
                file.write("=" * 30 + "\n")
                for dish in self.selected_dishes:
                    file.write(f"• {dish.name} - {dish.price:.2f} ₽\n")
                total = sum(dish.price for dish in self.selected_dishes)
                file.write("=" * 30 + "\n")
                file.write(f"ИТОГО: {total:.2f} ₽\n")
            QMessageBox.information(self, "Успех", "Заказ экспортирован")

    def show_order_history(self):
        dialog = OrderHistoryDialog(self)
        dialog.exec()

    def show_add_dish_dialog(self):
        dialog = AddDishDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dish_data = dialog.get_dish_data()

            if not dish_data['name']:
                QMessageBox.warning(self, "Ошибка", "Введите название блюда!")
                return

            try:
                dish_id = self.db_manager.add_new_dish(
                    dish_data['name'],
                    dish_data['price'],
                    dish_data['image_path']
                )

                QMessageBox.information(
                    self, "Успех",
                    f"Блюдо '{dish_data['name']}' добавлено!\nID: {dish_id}"
                )
                self.load_dishes()

            except Exception as e:
                QMessageBox.critical(
                    self, "Ошибка", f"Не удалось добавить блюдо:\n{str(e)}"
                )

    def show_delete_dish_dialog(self):
        if not self.dishes:
            QMessageBox.information(self, "Информация", "Нет блюд для удаления")
            return

        dialog = DeleteDishDialog(self.dishes, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            dish_id = dialog.get_selected_dish_id()
            if dish_id:
                self.delete_dish(dish_id)

    def delete_dish(self, dish_id):
        dish_to_delete = next((d for d in self.dishes if d.id == dish_id), None)
        if not dish_to_delete:
            return

        reply = QMessageBox.question(
            self, "Подтверждение удаления",
            f"Вы уверены, что хотите удалить блюдо '{dish_to_delete.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db_manager.delete_dish(dish_id)
                QMessageBox.information(self, "Успех", "Блюдо удалено!")
                self.load_dishes()
            except Exception as e:
                QMessageBox.critical(
                    self, "Ошибка", f"Не удалось удалить блюдо:\n{str(e)}"
                )


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
