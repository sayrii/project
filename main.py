import sys
import sqlite3
import csv
from dataclasses import dataclass
from datetime import datetime
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QAbstractTableModel
from PyQt6.QtGui import QFont, QPixmap, QAction
from PyQt6.QtWidgets import (QMainWindow, QDialog, QMessageBox,
                             QFileDialog, QCheckBox, QWidget,
                             QVBoxLayout, QHBoxLayout, QLabel,
                             QTableView, QGroupBox, QScrollArea,
                             QPushButton, QMenu, QMenuBar, QStatusBar,
                             QInputDialog, QGridLayout)


@dataclass
class Dish:
    """класс для представления блюда"""
    id: int
    name: str
    price: float
    image_path: str
    selected: bool = False


class DatabaseManager:
    """менеджер базы данных"""

    def __init__(self, db_name="dishes.db"):
        self.db_name = db_name
        self.init_database()

    def init_database(self):
        """инициализация бд"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dishes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                image_path TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_amount REAL NOT NULL,
                order_date TEXT NOT NULL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                dish_id INTEGER,
                quantity INTEGER,
                FOREIGN KEY (order_id) REFERENCES orders (id),
                FOREIGN KEY (dish_id) REFERENCES dishes (id)
            )
        ''')

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
        """получение всех блюд"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price, image_path FROM dishes")
        dishes = [Dish(*row) for row in cursor.fetchall()]
        conn.close()
        return dishes

    def save_order(self, selected_dishes, total_amount):
        """сохранение заказа"""
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
                "INSERT INTO order_details (order_id, dish_id, quantity) VALUES (?, ?, ?)",
                (order_id, dish.id, 1)
            )

        conn.commit()
        conn.close()
        return order_id

    def get_order_history(self):
        """получение истории заказов"""
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


class OrdersTableModel(QAbstractTableModel):
    """модель таблицы заказов"""

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
        if (role == Qt.ItemDataRole.DisplayRole and
                orientation == Qt.Orientation.Horizontal):
            return self.headers[section]
        return None


class DishWidget(QWidget):
    """виджет отображения блюда"""

    def __init__(self, dish, on_selection_change):
        super().__init__()
        self.dish = dish
        self.on_selection_change = on_selection_change
        self.init_ui()

    def init_ui(self):
        """инициализация UI"""
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
        """загрузка изображения"""
        try:
            pixmap = QPixmap(self.dish.image_path)
            if pixmap.isNull():
                raise Exception("Image not found")

            image_label = QLabel()
            image_label.setPixmap(pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio))
            layout.addWidget(image_label)
        except Exception:
            error_label = QLabel("Нет\nизобр.")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet("color: #999;")
            layout.addWidget(error_label)

    def on_checkbox_changed(self, state):
        """обработчик чекбокса"""
        self.dish.selected = (state == Qt.CheckState.Checked.value)
        self.on_selection_change()


class OrderHistoryDialog(QDialog):
    """диалог истории заказов"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()
        self.init_ui()
        self.setup_connections()
        self.load_orders()

    def init_ui(self):
        """инициализация UI"""
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
        """настройка соединений"""
        self.close_btn.clicked.connect(self.close)
        self.export_csv_btn.clicked.connect(self.export_to_csv)

    def load_orders(self):
        """загрузка заказов"""
        orders = self.db_manager.get_order_history()
        model = OrdersTableModel(orders)
        self.orders_table.setModel(model)
        self.orders_table.resizeColumnsToContents()

    def export_to_csv(self):
        """экспорт в CSV"""
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


template = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Заказ из ресторана</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            border-bottom: 3px solid #e74c3c;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #e74c3c;
            margin: 0;
        }
        .order-info {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .dishes-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .dishes-table th {
            background: #e74c3c;
            color: white;
            padding: 12px;
            text-align: left;
        }
        .dishes-table td {
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }
        .dishes-table tr:nth-child(even) {
            background: #f8f9fa;
        }
        .total-section {
            background: #2ecc71;
            color: white;
            padding: 20px;
            border-radius: 5px;
            text-align: center;
            margin-top: 20px;
        }
        .total-amount {
            font-size: 24px;
            font-weight: bold;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            color: #7f8c8d;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🍝 Ресторан "Чайхана"</h1>
            <p>Ваш заказ</p>
        </div>

        <div class="order-info">
            <h3>Детали заказа</h3>
            <p><strong>Дата:</strong> {{order_date}}</p>
            <p><strong>Количество блюд:</strong> {{dishes_count}}</p>
        </div>

        <table class="dishes-table">
            <thead>
                <tr>
                    <th>Блюдо</th>
                    <th>Цена</th>
                </tr>
            </thead>
            <tbody>
                {{dishes_rows}}
            </tbody>
        </table>

        <div class="total-section">
            <h3>Общая сумма заказа:</h3>
            <div class="total-amount">{{total_amount}} ₽</div>
        </div>

        <div class="footer">
            <p>Спасибо за ваш заказ! Приятного аппетита!</p>
        </div>
    </div>
</body>
</html>
'''


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

        self.actionExport = QtGui.QAction(parent=MainWindow)
        self.actionExport.setObjectName("actionExport")

        self.actionViewOrders = QtGui.QAction(parent=MainWindow)
        self.actionViewOrders.setObjectName("actionViewOrders")

        self.menu.addAction(self.actionExport)
        self.menu.addAction(self.actionViewOrders)
        self.menubar.addAction(self.menu.menuAction())

        MainWindow.setMenuBar(self.menubar)

        self.statusbar = QtWidgets.QStatusBar(parent=MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Чайхана - Лучший выбор блюд"))
        self.titleLabel.setText(_translate("MainWindow", "Выберите блюда"))
        self.totalGroupBox.setTitle(_translate("MainWindow", "Итого"))
        self.confirmButton.setText(_translate("MainWindow", "Подтвердить заказ"))
        self.menu.setTitle(_translate("MainWindow", "Меню"))
        self.actionExport.setText(_translate("MainWindow", "Экспорт заказа"))
        self.actionViewOrders.setText(_translate("MainWindow", "Просмотр заказов"))


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    """главное окно приложения"""

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
        """настройка соединений"""
        self.confirmButton.clicked.connect(self.confirm_order)
        self.actionExport.triggered.connect(self.export_order_html)
        self.actionViewOrders.triggered.connect(self.show_order_history)

    def load_dishes(self):
        """загрузка блюд"""
        self.dishes = self.db_manager.get_all_dishes()
        grid_layout = self.dishesGridLayout

        row, col = 0, 0
        for dish in self.dishes:
            dish_widget = DishWidget(dish, self.update_total)
            grid_layout.addWidget(dish_widget, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1

    def update_total(self):
        """обновление суммы"""
        self.selected_dishes = [dish for dish in self.dishes if dish.selected]
        total = sum(dish.price for dish in self.selected_dishes)
        self.totalLabel.setText(f"{total:.2f} ₽")

        status_text = f"Выбрано {len(self.selected_dishes)} блюд"
        self.statusbar.showMessage(status_text)

    def confirm_order(self):
        """подтверждение заказа"""
        if not self.selected_dishes:
            QMessageBox.warning(self, "Внимание", "Выберите блюда!")
            return

        total = sum(dish.price for dish in self.selected_dishes)
        order_id = self.db_manager.save_order(self.selected_dishes, total)

        QMessageBox.information(
            self,
            "Успех",
            f"Заказ #{order_id} сохранен!\nСумма: {total:.2f} ₽"
        )

        for dish in self.dishes:
            dish.selected = False
        self.update_total()
        self.reset_checkboxes()

    def reset_checkboxes(self):
        """сброс чекбоксов"""
        for i in range(self.dishesGridLayout.count()):
            widget = self.dishesGridLayout.itemAt(i).widget()
            if isinstance(widget, DishWidget):
                widget.checkbox.setChecked(False)

    def export_order_html(self):
        """экспорт заказа в HTML"""
        if not self.selected_dishes:
            QMessageBox.warning(self, "Внимание", "Нет выбранных блюд!")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Экспорт HTML", "order.html", "HTML Files (*.html)"
        )
        if filename:
            try:
                self.generate_html_file(filename)
                QMessageBox.information(self, "Успех", "HTML файл создан")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка: {str(e)}")

    def generate_html_file(self, filename):
        total = sum(dish.price for dish in self.selected_dishes)
        current_date = datetime.now().strftime("%d.%m.%Y %H:%M")

        dishes_rows = ""
        for dish in self.selected_dishes:
            dishes_rows += f"<tr><td>{dish.name}</td><td>{dish.price:.2f} ₽</td></tr>\n"

        html_content = template.replace("{{order_date}}", current_date)
        html_content = html_content.replace("{{dishes_count}}", str(len(self.selected_dishes)))
        html_content = html_content.replace("{{dishes_rows}}", dishes_rows)
        html_content = html_content.replace("{{total_amount}}", f"{total:.2f}")

        with open(filename, 'w', encoding='utf-8') as file:
            file.write(html_content)

    def show_order_history(self):
        """показать историю заказов"""
        dialog = OrderHistoryDialog(self)
        dialog.exec()


def main():
    """главная функция"""
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
