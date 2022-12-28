import sys
import os
from os import path

from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, \
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox
from PyQt5.QtCore import Qt, QEvent, QObject, QCoreApplication, QTimer
from PyQt5 import QtGui
from PyQt5.QtGui import QIcon
from PyQt5 import QtCore

import win32gui
import win32ui
import win32con

import io
import win32clipboard
from PIL import Image


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super(MainWindow, self).__init__()

        # Class Instance Variables.
        self.mouse_relative_position_x = 0
        self.mouse_relative_position_y = 0
        self.button_window_height = 50
        self.region_x_pos = 0
        self.region_y_pos = 0
        self.region_width = 0
        self.region_height = 0
        self.screen_shoot_path = ""

        # Set the flags for this window.
        # The flag "Qt.FramelessWindowHint" is used to make the window frameless and translucent.
        # The flag "Qt.SubWindow" is used to hide this window from appears in the taskbar,
        # or to hide the icon from appears in the taskbar. Indicates that this widget is a sub-window.
        self.setWindowFlags(Qt.FramelessWindowHint)
        # Set the attributes for this window.
        # The attribute "Qt.WA_TranslucentBackground" Indicates that the widget should have a translucent
        # background, i.e., any non-opaque regions of the widgets will be translucent because the widget
        # will have an alpha channel. Setting this flag causes WA_NoSystemBackground to be set.
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Create an instance of the class ButtonWindow.
        self.button_window = ButtonWindow()

        # When the button close is clicked, then close this window.
        self.button_window.button_close.clicked.connect(self.close)

        # When the button save is clicked, then call method get_screen_region.
        self.button_window.button_save.clicked.connect(self.get_screen_region_and_open_save_file_dialog)

        # When the button clipboard is clicked, then call method get_screen_region.
        self.button_window.button_clipboard.clicked.connect(self.get_screen_region_and_hide_windows)

        # Create a QTimer instance.
        self.timer = QTimer(self)

        # Used to save the mouse different states, e.g. 0 is when the mouse left button is released.
        # "1" is when the mouse left button is pressed, and the window position is:
        # pos.x() > self.width() - 5 and pos.y() > self.height() - 5
        self.mouse_mode = 0

        # Create the stylesheet to make the window transparent.
        # If we want the property to apply only to one specific Widget , we can give it a name
        # using setObjectName() and use an ID Selector to refer to it.
        widget_stylesheet = "QWidget#central_widget {" \
                            "border-color: rgba(255, 0, 0, 255);" \
                            "border-left-color: rgba(255, 0, 0, 255);" \
                            "border-right-color: rgba(255, 0, 0, 255);" \
                            "border-bottom-color: rgba(255, 0, 0, 255);" \
                            "border-style: dashed;" \
                            "border-top-width: 4px;" \
                            "border-left-width: 4px;" \
                            "border-right-width: 4px;" \
                            "border-bottom-width: 4px;" \
                            "border-radius: 4px;" \
                            "background-color: rgba(255, 255, 255, 2);" \
                            "}"

        # Create the central widget.
        self.central_widget = QWidget(self)
        self.central_widget.setStyleSheet(widget_stylesheet)
        self.central_widget.setMouseTracking(True)
        self.central_widget.installEventFilter(self)
        self.central_widget.setObjectName("central_widget")

        # Set the central widget for the main window.
        self.setCentralWidget(self.central_widget)

        # Define the initial geometry for the window.
        screen_width = QApplication.primaryScreen().size().width()
        screen_height = QApplication.primaryScreen().size().height()
        self.setGeometry(int(screen_width / 2) - int(self.geometry().width() / 2),  # x position
                         int(screen_height / 2) - int(self.geometry().height() / 2),  # y position
                         400,  # width
                         300)  # height

        # Set an icon for this window.
        file_name = os.path.dirname(os.path.realpath(__file__)) + "\\Images\\capture.ico"
        if path.exists(file_name):
            self.setWindowIcon(QIcon(file_name))

        # set windows minimum size.
        self.setMinimumSize(300, 100)

    def open_save_file_dialog(self) -> str:
        # Get current directory.
        current_directory = os.path.dirname(os.path.realpath(__file__))

        # Sets the filter used by the model to filters. The filter is
        # used to specify the kind of files that should be shown.
        # filter = "text files (*.jpg *.JPG)"
        filter = "text files (*.bmp *.BMP)"

        # Open the Save File Dialog for the user to choose the location and the name for the image to save.
        # The method "getSaveFileName" return a tuple with two values (file name and file extension),
        # using [0] we get the first element of the tuple.
        path_file_name = QFileDialog.getSaveFileName(self, 'Choose where to save the screen capture image',
                                                     current_directory, filter)[0]
        # Return the path and the name to save the screen captured image.
        return path_file_name

    @QtCore.pyqtSlot()
    def get_screen_region_and_open_save_file_dialog(self) -> None:
        # Save a copy of the selected region X, Y, Width and Height.
        self.region_x_pos = self.x()
        self.region_y_pos = self.y()
        self.region_width = self.width()
        self.region_height = self.height()
        # Open the Save File Dialog for the user to choose the location and the name
        # for the image to save.
        self.screen_shoot_path = self.open_save_file_dialog()
        # Hide both windows.
        self.hide()
        self.button_window.hide()
        # Call show_windows after 500ms.
        # This is done to give time for windows to hide and then, take the screenshot.
        self.timer.singleShot(500, self.save_screen_region_to_file_and_show_windows)

    @QtCore.pyqtSlot()
    def save_screen_region_to_file_and_show_windows(self) -> None:
        # Get a screenshot of the region area selected by the user.
        if len(self.screen_shoot_path) > 0:
            self.save_screen_region_to_file(self.region_x_pos, self.region_y_pos,
                                            self.region_width, self.region_height, self.screen_shoot_path)
        # Show both windows.
        self.show()
        self.button_window.show()
        # To bring the button window to the front.
        self.button_window.activateWindow()
        self.button_window.raise_()

    @staticmethod
    def save_screen_region_to_file(x: int, y: int, width: int, height: int, full_path_and_image: str):
        """
        This method save a screenshot of passed screen area. It uses the win32gui library
        to be able to grab a screen area in any of the desktops available, if more than one.
        :param x:               Upper-left corner X position of selected screen area.
        :param y:               Upper-left corner Y position of selected screen area.
        :param width:           Width of selected screen area.
        :param height:          Height of selected screen area.
        :param full_path_and_image:    Path and name of the file used to save the image.
        :return:                Nothing.
        """
        # Grab a handle to the main desktop window.
        desktop_window = win32gui.GetDesktopWindow()
        # Create a device context (DC).
        window_device_context = win32gui.GetWindowDC(desktop_window)
        # Creates a DC object from an integer handle.
        img_dc = win32ui.CreateDCFromHandle(window_device_context)
        # Create a memory based device context.
        mem_dc = img_dc.CreateCompatibleDC()
        # Create a bitmap object.
        screenshot = win32ui.CreateBitmap()
        screenshot.CreateCompatibleBitmap(img_dc, width, height)
        mem_dc.SelectObject(screenshot)
        # Copy the screen into our memory device context.
        mem_dc.BitBlt((0, 0), (width, height), img_dc, (x, y), win32con.SRCCOPY)
        # Save the bitmap to a file.
        screenshot.SaveBitmapFile(mem_dc, full_path_and_image)
        # Free created objects.
        img_dc.DeleteDC()
        mem_dc.DeleteDC()
        win32gui.DeleteObject(screenshot.GetHandle())

    @staticmethod
    def copy_image_from_file_to_clipboard(full_path_and_image: str) -> None:
        # Open an image from file using PIL library.
        image = Image.open(full_path_and_image)
        # Buffered I/O implementation using an in-memory bytes buffer.
        output = io.BytesIO()
        # Convert the image to RGB and save it into the buffer.
        image.convert(mode="RGB").save(output, format="BMP")
        # Remove the first 14 bytes of the image, which is the header of a BMP file.
        # 14 because a BMP file has a 14-byte header.
        data = output.getvalue()[14:]
        # Close the buffer.
        output.close()
        #
        win32clipboard.OpenClipboard()
        #
        win32clipboard.EmptyClipboard()
        #
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        #
        win32clipboard.CloseClipboard()

    @QtCore.pyqtSlot()
    def get_screen_region_and_hide_windows(self) -> None:
        # Save a copy of the selected region X, Y, Width and Height.
        self.region_x_pos = self.x()
        self.region_y_pos = self.y()
        self.region_width = self.width()
        self.region_height = self.height()
        # Hide both windows.
        self.hide()
        self.button_window.hide()
        # Call show_windows after 500ms.
        # This is done to give time for windows to hide and then, take the screenshot.
        self.timer.singleShot(500, self.copy_screen_region_to_clipboard_and_show_windows)

    @QtCore.pyqtSlot()
    def copy_screen_region_to_clipboard_and_show_windows(self) -> None:
        # Get an image from a screen region and put it in the clipboard as an image.
        self.copy_screen_region_to_clipboard(self.region_x_pos, self.region_y_pos,
                                             self.region_width, self.region_height)
        # Show both windows.
        self.show()
        self.button_window.show()
        # Code used to bring the button window to the front.
        self.button_window.activateWindow()
        self.button_window.raise_()

    @staticmethod
    def copy_screen_region_to_clipboard(x: int, y: int, width: int, height: int) -> None:
        """
        Get an image from a screen region and put it in the clipboard as an image.
        :param x:       Region upper-left corner x coordinate.
        :param y:       Region upper-left corner y coordinate.
        :param width:   Region width dimension.
        :param height:  Region height dimension.
        :return:        None.
        """
        # Grab a handle to the main desktop window.
        desktop_window = win32gui.GetDesktopWindow()
        # Create a device context (DC).
        window_device_context = win32gui.GetWindowDC(desktop_window)
        # Creates a DC object from an integer handle.
        img_dc = win32ui.CreateDCFromHandle(window_device_context)
        # Create a memory based device context.
        mem_dc = img_dc.CreateCompatibleDC()
        # Create a bitmap object.
        screenshot = win32ui.CreateBitmap()
        screenshot.CreateCompatibleBitmap(img_dc, width, height)
        mem_dc.SelectObject(screenshot)
        # Copy the screen into our memory device context.
        mem_dc.BitBlt((0, 0), (width, height), img_dc, (x, y), win32con.SRCCOPY)

        # Load into PIL image.
        bmpinfo = screenshot.GetInfo()
        bmpstr = screenshot.GetBitmapBits(True)
        screenshot_image = Image.frombuffer('RGB',
                                            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                                            bmpstr, 'raw', 'BGRX', 0, 1)

        # Free win32gui created objects.
        img_dc.DeleteDC()
        mem_dc.DeleteDC()
        win32gui.DeleteObject(screenshot.GetHandle())

        # Buffered I/O implementation using an in-memory bytes buffer.
        output = io.BytesIO()
        # Convert the image to RGB and save it into the buffer.
        screenshot_image.convert(mode="RGB").save(output, format="BMP")
        # Remove the first 14 bytes of the image, which is the header of a BMP file.
        # 14 because a BMP file has a 14-byte header.
        data = output.getvalue()[14:]
        # Close the buffer.
        output.close()

        # Copy image to clipboard.
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

    # Overwrite the method mousePressEvent for class QMainWindow.
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            # Get the cursor position relative to the widget that receives the mouse event.
            self.mouse_relative_position_x = event.pos().x()
            self.mouse_relative_position_y = event.pos().y()
            # The mouse event is handled by this widget.
            event.accept()
        else:
            # The mouse event is not handle by this widget.
            event.ignore()

    # Overwrite the method mouseReleaseEvent for class QMainWindow.
    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            # Change the mouse cursor to be the standard arrow cursor.
            QApplication.setOverrideCursor(Qt.ArrowCursor)
            # Set mouse mode to 0, meaning that none of the buttons are pressed.
            self.mouse_mode = 0
            # The mouse event is handled by this widget.
            event.accept()
        else:
            # The mouse event is not handle by this widget.
            event.ignore()

    # Override the method resizeEvent for class MainWindow.
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """
        This method will be called every time the main window is resized.
        It is used to resize the button window to match the width of the
        main window.
        :param event: Resize event object.
        :return: Nothing.
        """
        # Set geometry for the button window whenever the main window change its size.
        self.button_window.setGeometry(self.x(),  # x position
                                       self.y() + self.height(),  # y position
                                       self.width(),  # width
                                       self.button_window_height)  # height
        # Pass the event to the main window.
        QMainWindow.resizeEvent(self, event)

    # Override method eventFilter for class MainWindow.
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:

        # If the mouse moved.
        if event.type() == QEvent.MouseMove:
            # Get mouse relative position respect the window.
            pos = event.pos()

            # To bring the button window to the front.
            self.button_window.show()
            self.button_window.activateWindow()
            self.button_window.raise_()

            # If none of buttons were pressed, then change the mouse cursor
            # when the mouse reach the edge of the window to let the user know
            # that the window can be resized.
            if event.buttons() == Qt.NoButton:
                # Change the mouse cursor when pointer reach the bottom-right corner.
                if pos.x() > self.width() - 5 and pos.y() > self.height() - 5:
                    QApplication.setOverrideCursor(Qt.SizeFDiagCursor)
                # Change the mouse cursor when pointer reach the top-left corner.
                elif pos.x() < 5 and pos.y() < 5:
                    QApplication.setOverrideCursor(Qt.SizeFDiagCursor)
                # Change the mouse cursor when pointer reach the top-right corner.
                elif pos.x() > self.width() - 5 and pos.y() < 5:
                    QApplication.setOverrideCursor(Qt.SizeBDiagCursor)
                # Change the mouse cursor when pointer reach the bottom-left corner.
                elif pos.x() < 5 and pos.y() > self.height() - 5:
                    QApplication.setOverrideCursor(Qt.SizeBDiagCursor)
                # Change the mouse cursor when pointer reach the left and right border.
                elif pos.x() > self.width() - 5 or pos.x() < 5:
                    QApplication.setOverrideCursor(Qt.SizeHorCursor)
                # Change the mouse cursor when pointer reach the top and bottom border.
                elif pos.y() > self.height() - 5 or pos.y() < 5:
                    QApplication.setOverrideCursor(Qt.SizeVerCursor)
                # Change the mouse cursor to the standard arrow cursor.
                else:
                    QApplication.setOverrideCursor(Qt.ArrowCursor)

            # If the left button was pressed, then change the mouse cursor
            # when it reaches the edge of the window and also adjust the geometry
            # of the window.
            if event.buttons() & Qt.LeftButton:

                # When the mouse is in the bottom-right corner.
                # If the X mouse position is greater than the window width - 10,
                # and if the Y mouse position is greater than the window height - 10,
                # then adjust window geometry.
                if pos.x() > self.width() - 10 and pos.y() > self.height() - 10 \
                        and (self.mouse_mode == 0 or self.mouse_mode == 1):
                    self.mouse_mode = 1
                    QApplication.setOverrideCursor(Qt.SizeFDiagCursor)
                    self.setGeometry(self.x(), self.y(), pos.x(), pos.y())

                # When the mouse is in the top-left corner.
                # If the X mouse position is less than 10,
                # and if the Y mouse position is less than 10,
                # then adjust window geometry.
                elif pos.x() < 10 and pos.y() < 10 \
                        and (self.mouse_mode == 0 or self.mouse_mode == 2):
                    self.mouse_mode = 2
                    QApplication.setOverrideCursor(Qt.SizeFDiagCursor)
                    self.setGeometry(self.x() + pos.x(), self.y() + pos.y(),
                                     self.width() - pos.x(), self.height() - pos.y())

                # When the mouse is in the top-right corner.
                # If the X mouse position is greater than the window width - 10,
                # and if the Y mouse position is less than 10,
                # then adjust window geometry.
                elif pos.x() > self.width() - 10 and pos.y() < 10 \
                        and (self.mouse_mode == 0 or self.mouse_mode == 3):
                    self.mouse_mode = 3
                    QApplication.setOverrideCursor(Qt.SizeBDiagCursor)
                    self.setGeometry(self.x(), self.y() + pos.y(),
                                     pos.x(), self.height() - pos.y())

                # When the mouse is in the bottom-left corner.
                # If the X mouse position is less than 10,
                # and if the Y mouse position is greater than height - 10,
                # then adjust window geometry.
                elif pos.x() < 10 and pos.y() > self.height() - 10 \
                        and (self.mouse_mode == 0 or self.mouse_mode == 4):
                    self.mouse_mode = 4
                    QApplication.setOverrideCursor(Qt.SizeBDiagCursor)
                    self.setGeometry(self.x() + pos.x(), self.y(),
                                     self.width() - pos.x(), pos.y())

                # When the mouse is on the window right border.
                # If the X mouse position is greater than the window width - 5,
                # then adjust window geometry.
                elif pos.x() > self.width() - 5 and 0 < pos.y() < self.height() \
                        and (self.mouse_mode == 0 or self.mouse_mode == 5):
                    self.mouse_mode = 5
                    QApplication.setOverrideCursor(Qt.SizeHorCursor)
                    self.setGeometry(self.x(), self.y(), pos.x(), self.height())

                # When the mouse is on the window left border.
                # If the X mouse position is less than 5,
                # then adjust window geometry.
                elif pos.x() < 5 and 0 < pos.y() < self.height() \
                        and (self.mouse_mode == 0 or self.mouse_mode == 6):
                    self.mouse_mode = 6
                    QApplication.setOverrideCursor(Qt.SizeHorCursor)
                    if self.width() - pos.x() > self.minimumWidth():
                        self.setGeometry(self.x() + pos.x(), self.y(), self.width() - pos.x(), self.height())

                # When the mouse is on the window bottom border.
                # If the Y mouse position is greater than the window height,
                # then adjust window geometry.
                elif pos.y() > self.height() - 5 and 0 < pos.x() < self.width() \
                        and (self.mouse_mode == 0 or self.mouse_mode == 7):
                    self.mouse_mode = 7
                    QApplication.setOverrideCursor(Qt.SizeVerCursor)
                    self.setGeometry(self.x(), self.y(), self.width(), pos.y())

                # When the mouse is on the window top border.
                # If the Y mouse position is less than 5,
                # then adjust window geometry.
                elif pos.y() < 5 and 0 < pos.x() < self.width() \
                        and (self.mouse_mode == 0 or self.mouse_mode == 8):
                    self.mouse_mode = 8
                    QApplication.setOverrideCursor(Qt.SizeVerCursor)
                    if self.height() - pos.y() > self.minimumHeight():
                        self.setGeometry(self.x(), self.y() + pos.y(), self.width(), self.height() - pos.y())

                # If the X mouse position is greater than 10 and less than window width
                # and the Y mouse position is greater than 10 and less than window height.
                # Then move window to a new position.
                elif 10 < pos.x() < self.width() - 10 and 10 < pos.y() < self.height() - 10 \
                        and (self.mouse_mode == 0 or self.mouse_mode == 9):
                    self.mouse_mode = 9
                    # Change the mouse cursor to cursor used for elements that are used to
                    # resize top-level windows in any direction.
                    QApplication.setOverrideCursor(Qt.SizeAllCursor)
                    # Move the widget when the mouse is dragged.
                    self.move(event.globalPos().x() - self.mouse_relative_position_x,
                              event.globalPos().y() - self.mouse_relative_position_y)
                    # Set geometry for the button_window.
                    self.button_window.setGeometry(self.x(),  # x position
                                                   self.y() + self.height(),  # y position
                                                   self.width(),  # width
                                                   self.button_window_height)  # height
                else:
                    # Change the mouse cursor to be the standard arrow cursor.
                    QApplication.setOverrideCursor(Qt.ArrowCursor)

        elif event.type() == QEvent.Show:
            # Set geometry for the button_window.
            self.button_window.setGeometry(self.x(),  # x position
                                           self.y() + self.height(),  # y position
                                           self.width(),  # width
                                           self.button_window_height)  # height
            # Show the window.
            self.button_window.show()

        else:
            # return super(MainWindow, self).eventFilter(watched, event)
            return False

        # This function does not cause an immediate repaint; instead it schedules a paint
        # event for processing when Qt returns to the main event loop. This permits Qt to
        # optimize for more speed and less flicker than a call to repaint() does.
        self.central_widget.update()
        # Processes all pending events for the calling thread according to the specified
        # flags until there are no more events to process.
        QCoreApplication.processEvents()

        return True


class ButtonWindow(QWidget):
    def __init__(self) -> None:
        super(ButtonWindow, self).__init__()

        # Set the flags for this window.
        # The flag "Qt.FramelessWindowHint" is used to make the window frameless and translucent.
        # The flag "Qt.SubWindow" is used to hide this window from appears in the taskbar,
        # or to hide the icon from appears in the taskbar. Indicates that this widget is a sub-window.
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        # Set the attributes for this window.
        # The attribute "Qt.WA_TranslucentBackground" Indicates that the widget should have a translucent
        # background, i.e., any non-opaque regions of the widgets will be translucent because the widget
        # will have an alpha channel. Setting this flag causes WA_NoSystemBackground to be set.
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Create the stylesheet to make the window transparent.
        # If we want the property to apply only to one specific Widget , we can give it a name
        # using setObjectName() and use an ID Selector to refer to it.
        widget_stylesheet = "QWidget#button_window {" \
                            "background-color: rgba(255, 255, 255, 2);" \
                            "}"

        button_stylesheet = "QPushButton {" \
                            "color: rgb(255, 255, 255);" \
                            "font: 75 10pt FreeSans;" \
                            "background-color: rgba(6, 104, 249, 255);" \
                            "border-top-color: rgba(151, 222, 247, 255);" \
                            "border-left-color: rgba(151, 222, 247, 255);" \
                            "border-right-color: rgba(4, 57, 135, 255);" \
                            "border-bottom-color: rgba(4, 57, 135,255);" \
                            "border-style: inset;" \
                            "border-top-width: 2px;" \
                            "border-left-width: 2px;" \
                            "border-right-width: 3px;" \
                            "border-bottom-width: 3px;" \
                            "border-radius: 5px;" \
                            "}"

        # Create a button to capture the screen and save it to file.
        self.button_save = QPushButton("Save to File")
        self.button_save.setFixedSize(85, 30)
        self.button_save.setMouseTracking(True)
        self.button_save.installEventFilter(self)
        # self.button_capture_image.setStyleSheet(button_stylesheet)

        # Create a button to capture the screen and copy to clipboard.
        self.button_clipboard = QPushButton("Copy to Clipboard")
        self.button_clipboard.setFixedSize(100, 30)
        self.button_clipboard.setMouseTracking(True)
        self.button_clipboard.installEventFilter(self)
        # self.button_clipboard.setStyleSheet(button_stylesheet)

        # Create a button to close the application.
        self.button_close = QPushButton("Close")
        self.button_close.setFixedSize(85, 30)
        self.button_close.setMouseTracking(True)
        self.button_close.installEventFilter(self)
        # self.button_close.setStyleSheet(button_stylesheet)

        # Create a horizontal layout with the buttons.
        horizontal_layout = QHBoxLayout()
        horizontal_layout.addStretch(1)
        horizontal_layout.addWidget(self.button_save)
        horizontal_layout.addStretch(1)
        horizontal_layout.addWidget(self.button_clipboard)
        horizontal_layout.addStretch(1)
        horizontal_layout.addWidget(self.button_close)
        horizontal_layout.addStretch(1)

        # Create a vertical layout with the horizontal layout.
        vert_layout = QVBoxLayout()
        vert_layout.addStretch(1)
        vert_layout.addLayout(horizontal_layout)
        vert_layout.addStretch(1)

        # Set the widget layout.
        self.setLayout(vert_layout)
        self.setStyleSheet(widget_stylesheet)
        self.setObjectName("button_window")

    # Override method eventFilter for class QWidget.
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        # If the mouse moved.
        if event.type() == QEvent.MouseMove:
            QApplication.setOverrideCursor(Qt.ArrowCursor)
            return True
        else:
            return False


def main():
    # Create a QApplication object. It manages the GUI application's control flow and main settings.
    # It handles widget specific initialization, finalization.
    # For any GUI application using Qt, there is precisely one QApplication object.
    app = QApplication([])
    # Create an instance of the class MainWindow.
    window = MainWindow()
    # Show the window.
    window.show()
    # Start Qt event loop.
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
