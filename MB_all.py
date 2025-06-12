import sys
import pickle
from PyQt6.QtWidgets import QGraphicsPathItem
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsEllipseItem, QGraphicsTextItem, QVBoxLayout, QWidget, QPushButton,
    QFileDialog, QLabel, QInputDialog, QHBoxLayout, QMessageBox
)
from PyQt6.QtGui import QPen, QBrush, QPainterPath, QColor
from PyQt6.QtCore import Qt, QPointF

class StateItem(QGraphicsEllipseItem):
    def __init__(self, name, x, y):
        super().__init__(-30, -30, 60, 60)
        self.setBrush(QBrush(Qt.GlobalColor.white))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setPos(x, y)
        self.name = name
        self.text = QGraphicsTextItem(name, self)
        self.text.setDefaultTextColor(QColor(Qt.GlobalColor.black))
        self.text.setPos(-self.text.boundingRect().width() / 2, -self.text.boundingRect().height() / 2)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            self.update_transitions()
        return super().itemChange(change, value)

    def update_transitions(self):
        if self.scene():
            for transition in self.scene().transitions:
                if transition.start_item == self or transition.end_item == self:
                    transition.update_position()

class TransitionItem(QGraphicsPathItem):
    def __init__(self, start_item, end_item, input_signal, output_signal):
        super().__init__()
        self.start_item = start_item
        self.end_item = end_item
        self.input_signal = input_signal
        self.output_signal = output_signal
        self.setPen(QPen(Qt.GlobalColor.black, 2))
        self.arrow_size = 10
        self.text = QGraphicsTextItem(f"{input_signal}/{output_signal}")
        self.text.setDefaultTextColor(QColor(Qt.GlobalColor.darkRed))
        self.update_position()

    def update_position(self):
        line = QPainterPath()
        start_pos = self.start_item.pos()
        end_pos = self.end_item.pos()
        line.moveTo(start_pos)
        line.lineTo(end_pos)
        self.setPath(line)

        mid_point = (start_pos + end_pos) / 2
        if self.text.scene() is None and self.scene() is not None:
            self.scene().addItem(self.text)
        self.text.setPos(mid_point)

class AutomatonScene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.states = {}
        self.transitions = []
        self.current_state = None

    def add_state(self, name, x, y):
        if name in self.states:
            return
        state = StateItem(name, x, y)
        self.addItem(state)
        self.states[name] = state

    def add_transition(self, start_name, end_name, input_signal, output_signal):
        if start_name not in self.states or end_name not in self.states:
            return
        start_item = self.states[start_name]
        end_item = self.states[end_name]
        transition = TransitionItem(start_item, end_item, input_signal, output_signal)
        self.addItem(transition)
        self.transitions.append(transition)

    def clear_scene(self):
        for item in self.items():
            self.removeItem(item)
        self.states.clear()
        self.transitions.clear()
        self.current_state = None

class AutomatonView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.scene = AutomatonScene()
        self.view = QGraphicsView(self.scene)
        layout.addWidget(self.view)

        button_layout = QHBoxLayout()
        self.add_state_button = QPushButton("Добавить состояние")
        self.add_transition_button = QPushButton("Добавить переход")
        self.save_button = QPushButton("Сохранить")
        self.load_button = QPushButton("Загрузить")
        self.set_start_button = QPushButton("Задать начальное состояние")
        self.load_second_button = QPushButton("Загрузить второй автомат")
        self.merge_seq_button = QPushButton("Объединить (последовательно)")
        self.merge_par_button = QPushButton("Объединить (параллельно)")
        self.process_input_button = QPushButton("Обработать сигнал")

        self.add_state_button.clicked.connect(self.add_state)
        self.add_transition_button.clicked.connect(self.add_transition)
        self.save_button.clicked.connect(self.save)
        self.load_button.clicked.connect(self.load)
        self.set_start_button.clicked.connect(self.set_start_state)
        self.load_second_button.clicked.connect(self.load_second_automaton)
        self.merge_seq_button.clicked.connect(lambda: self.merge_automatons(mode="sequential"))
        self.merge_par_button.clicked.connect(lambda: self.merge_automatons(mode="parallel"))
        self.process_input_button.clicked.connect(self.process_input_signal)

        for btn in [self.add_state_button, self.add_transition_button, self.set_start_button, self.save_button,
                    self.load_button, self.load_second_button, self.merge_seq_button, self.merge_par_button,
                    self.process_input_button]:
            button_layout.addWidget(btn)

        layout.addLayout(button_layout)
        self.transition_list_label = QLabel("Переходы:")
        layout.addWidget(self.transition_list_label)

        self.second_scene_data = None

    def add_state(self):
        name, ok = QInputDialog.getText(self, "Имя состояния", "Введите имя состояния:")
        if ok and name:
            self.scene.add_state(name, 0, 0)

    def add_transition(self):
        start_name, ok1 = QInputDialog.getText(self, "Начальное состояние", "Введите имя начального состояния:")
        end_name, ok2 = QInputDialog.getText(self, "Конечное состояние", "Введите имя конечного состояния:")
        input_signal, ok3 = QInputDialog.getText(self, "Входной сигнал", "Введите входной сигнал:")
        output_signal, ok4 = QInputDialog.getText(self, "Выходной сигнал", "Введите выходной сигнал:")
        if ok1 and ok2 and ok3 and ok4:
            self.scene.add_transition(start_name, end_name, input_signal, output_signal)
            self.update_transition_list()

    def update_transition_list(self):
        text = "Переходы:\n"
        for t in self.scene.transitions:
            text += f"{t.start_item.name} -- {t.input_signal}/{t.output_signal} --> {t.end_item.name}\n"
        self.transition_list_label.setText(text)

    def save(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Сохранить автомат", "", "Pickle Files (*.pkl)")
        if filename:
            data = {
                'states': {name: (item.pos().x(), item.pos().y()) for name, item in self.scene.states.items()},
                'transitions': [(t.start_item.name, t.end_item.name, t.input_signal, t.output_signal) for t in self.scene.transitions],
                'current_state': self.scene.current_state
            }
            with open(filename, 'wb') as f:
                pickle.dump(data, f)

    def load(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Загрузить автомат", "", "Pickle Files (*.pkl)")
        if filename:
            try:
                with open(filename, 'rb') as f:
                    data = pickle.load(f)
                self.scene.clear_scene()
                for name, (x, y) in data['states'].items():
                    self.scene.add_state(name, x, y)
                for start, end, inp, out in data['transitions']:
                    self.scene.add_transition(start, end, inp, out)
                self.scene.current_state = data.get('current_state')
                self.update_transition_list()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка загрузки", f"Не удалось загрузить автомат: {str(e)}")

    def set_start_state(self):
        name, ok = QInputDialog.getText(self, "Начальное состояние", "Введите имя начального состояния:")
        if ok and name in self.scene.states:
            self.scene.current_state = name
            QMessageBox.information(self, "Успех", f"Начальное состояние: {name}")

    def load_second_automaton(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Загрузить второй автомат", "", "Pickle Files (*.pkl)")
        if filename:
            try:
                with open(filename, 'rb') as f:
                    self.second_scene_data = pickle.load(f)
                QMessageBox.information(self, "Успех", "Второй автомат загружен!")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить второй автомат: {str(e)}")

    def merge_automatons(self, mode="sequential"):
        if not self.second_scene_data:
            QMessageBox.warning(self, "Ошибка", "Сначала загрузите второй автомат!")
            return

        offset_x = 200
        second_states = self.second_scene_data['states']
        second_transitions = self.second_scene_data['transitions']
        mapping = {}
        for name, (x, y) in second_states.items():
            new_name = f"{name}_2"
            self.scene.add_state(new_name, x + offset_x, y)
            mapping[name] = new_name

        for start, end, inp, out in second_transitions:
            self.scene.add_transition(mapping[start], mapping[end], inp, out)

        if mode == "sequential":
            if not self.scene.current_state:
                QMessageBox.warning(self, "Ошибка", "Укажите начальное состояние первого автомата перед объединением!")
                return
            end_states = {t.end_item.name for t in self.scene.transitions if t.start_item.name == self.scene.current_state}
            for state in end_states:
                self.scene.add_transition(state, mapping[list(second_states.keys())[0]], 'λ', 'λ')

        self.update_transition_list()

    def process_input_signal(self):
        if not self.scene.current_state:
            QMessageBox.warning(self, "Ошибка", "Укажите начальное состояние!")
            return

        input_word, ok = QInputDialog.getText(self, "Входное слово", "Введите входное слово:")
        if not ok or not input_word:
            return

        current_state_name = self.scene.current_state
        output_word = ""

        for symbol in input_word:
            transitions = [
                t for t in self.scene.transitions
                if t.start_item.name == current_state_name and t.input_signal == symbol
            ]
            if not transitions:
                QMessageBox.warning(self, "Ошибка", f"Нет перехода из состояния '{current_state_name}' по сигналу '{symbol}'")
                return
            transition = transitions[0]
            output_word += transition.output_signal
            current_state_name = transition.end_item.name

        QMessageBox.information(self, "Результат", f"Выходное слово: {output_word}")

class AutomatonApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Редактор автомата Мили")
        self.view = AutomatonView()
        self.setCentralWidget(self.view)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = AutomatonApp()
    window.show()
    sys.exit(app.exec())
