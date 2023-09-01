import sys
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QListWidget, QListWidgetItem, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QProgressBar, QDialog)
from PyQt5.QtCore import QProcess, QObject, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QIcon

class CustomListItem(QWidget):
    def __init__(self, parent, package_name, is_installed=False):
        super().__init__()

        self.parent = parent
        self.package_name = package_name
        layout = QHBoxLayout()

        self.label = QLabel(self.package_name)
        layout.addWidget(self.label)

        self.installButton = QPushButton('Instalar' if not is_installed else 'Desinstalar')
        self.installButton.setFixedSize(100, 30)  # Tamaño fijo para los botones de "Instalar" y "Desinstalar"
        self.installButton.clicked.connect(self.installOrUninstallPackage if not is_installed else self.uninstallPackage)
        layout.addWidget(self.installButton)

        self.setLayout(layout)

    def installOrUninstallPackage(self):
        action = 'Desinstalar' if self.installButton.text() == 'Instalar' else 'Instalar'
        self.installButton.setText(action)
        if action == 'Desinstalar':
            self.installPackage()
        else:
            self.uninstallPackage()

    def installPackage(self):
        package_name = self.package_name.split('/')[-1]
        cmd = "pkexec"
        args = ["yay", "-S", "--noconfirm", package_name]
        self.parent.showCommandOutput(cmd, args)

    def uninstallPackage(self):
        package_name = self.package_name.split('/')[-1]
        cmd = "pkexec"
        args = ["yay", "-Rs", "--noconfirm", package_name]
        self.parent.showCommandOutput(cmd, args)

class OutputDialog(QDialog):
    def __init__(self, process, show_progress_bar=True):
        super().__init__()

        self.process = process

        layout = QVBoxLayout()

        self.textOutput = QTextEdit(self)
        self.textOutput.setReadOnly(True)
        layout.addWidget(self.textOutput)

        self.inputBar = QLineEdit(self)
        self.inputBar.setPlaceholderText("Introduce una respuesta...")
        self.inputBar.returnPressed.connect(self.sendInputToProcess)
        layout.addWidget(self.inputBar)

        if show_progress_bar:  # Mostrar la barra de progreso solo si se especifica
            self.progressBar = QProgressBar(self)
            layout.addWidget(self.progressBar)

        self.actionButton = QPushButton('Abortar', self)
        self.actionButton.clicked.connect(self.abortInstallation)
        layout.addWidget(self.actionButton)

        self.setLayout(layout)
        self.setWindowTitle('Progreso de instalación')
        self.setGeometry(350, 350, 500, 300)

    def sendInputToProcess(self):
        text = self.inputBar.text() + '\n'
        self.process.write(text.encode())
        self.inputBar.clear()

    def abortInstallation(self):
        self.process.terminate()
        self.textOutput.append("Instalación abortada.")
        self.actionButton.setEnabled(False)

    def processFinished(self):
        self.actionButton.setText('Finalizar')
        self.actionButton.setEnabled(True)
        self.actionButton.clicked.disconnect()
        self.actionButton.clicked.connect(self.close)

class App(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.searchBar = QLineEdit()
        self.searchBar.setPlaceholderText("Escriba para buscar...")
        self.searchBar.returnPressed.connect(self.searchPackages)
        layout.addWidget(self.searchBar)

        self.packageListWidget = QListWidget()
        layout.addWidget(self.packageListWidget)

        # Añadimos los dos nuevos botones aquí
        self.updateSystemButton = QPushButton("Actualizar sistema")
        self.updateSystemButton.clicked.connect(self.updateSystem)
        layout.addWidget(self.updateSystemButton)

        self.fixErrorsButton = QPushButton("Solucionar errores")
        self.fixErrorsButton.clicked.connect(self.fixErrors)
        layout.addWidget(self.fixErrorsButton)

        centralWidget = QWidget(self)
        centralWidget.setLayout(layout)
        self.setCentralWidget(centralWidget)

        self.setWindowTitle('Yay Packer')
        self.setGeometry(300, 300, 500, 400)

    # Método para manejar el clic en el botón "Actualizar sistema"
    def updateSystem(self):
        cmd = "pkexec"
        args = ["yay", "--noconfirm"]
        self.showCommandOutput(cmd, args, show_progress_bar=False)  # No mostrar la barra de progreso

    # Método para manejar el clic en el botón "Solucionar errores"
    def fixErrors(self):
        QDesktopServices.openUrl(QUrl("https://wiki.archlinux.org/title/Pacman_(Espa%C3%B1ol)"))

    def searchPackages(self):
        query = self.searchBar.text()
        if query:
            cmd = "yay"
            args = ["-Ss", query]
            self.process = QProcess()
            self.process.finished.connect(self.populateList)
            self.process.start(cmd, args)

    def populateList(self):
        output = str(self.process.readAllStandardOutput(), 'utf-8')
        package_pattern = re.compile(r"^(\S+/[\w-]+)\s+\S+")
        installed_pattern = re.compile(r"\(Instalado\)$")

        # Vamos a crear una lista de tuplas, cada tupla contiene el nombre del paquete y si está instalado.
        packages = [(match.group(1), bool(installed_pattern.search(line)))
                    for line in output.splitlines()
                    for match in [package_pattern.match(line)]
                    if match]

        self.packageListWidget.clear()
        for package, is_installed in packages:
            item = QListWidgetItem(self.packageListWidget)
            item_widget = CustomListItem(self, package, is_installed)
            item.setSizeHint(item_widget.sizeHint())
            self.packageListWidget.addItem(item)
            self.packageListWidget.setItemWidget(item, item_widget)

    def showCommandOutput(self, cmd, args, show_progress_bar=True):
        self.installProcess = QProcess()
        self.installProcess.readyReadStandardOutput.connect(self.updateOutput)
        self.installProcess.readyReadStandardError.connect(self.updateError)

        self.outputDialog = OutputDialog(self.installProcess, show_progress_bar=show_progress_bar)  # Pasa el parámetro aquí
        self.installProcess.finished.connect(self.outputDialog.processFinished)
        self.outputDialog.show()

        self.installProcess.start(cmd, args)

    def updateOutput(self):
        text = str(self.installProcess.readAllStandardOutput(), 'utf-8')
        self.outputDialog.textOutput.append(text)

    def updateError(self):
        text = str(self.installProcess.readAllStandardError(), 'utf-8')
        self.outputDialog.textOutput.append(text)

    def cleanup(self):
        if hasattr(self, 'installProcess') and self.installProcess.state() == QProcess.Running:
            self.installProcess.terminate()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = App()

    # Establece el ícono de la ventana principal
    icon_path = 'icon.png'  # Paso 2: Define la ruta a tu ícono
    app_icon = QIcon(icon_path)
    ex.setWindowIcon(app_icon)  # Paso 3: Establece el ícono

    app.aboutToQuit.connect(ex.cleanup)
    ex.show()
    sys.exit(app.exec_())
