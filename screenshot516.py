#!/usr/bin/env python3
# Python screenshot tool (fullscreen/area selection)
# Special thanks to @tomk11, @frakman1, @aspotton and @lucguislain for the improvements

import sys
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QPixmap, QScreen
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QSizePolicy
from PyQt5.QtWidgets import QGroupBox, QSpinBox, QCheckBox, QGridLayout
from PyQt5.QtWidgets import QPushButton, QHBoxLayout, QVBoxLayout
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import Qt
from Xlib import X, display, Xcursorfont

# Documentation for python-xlib here:
# http://python-xlib.sourceforge.net/doc/html/index.html

import cv2
import easyocr
from matplotlib import pyplot as plt
import numpy as np
from deep_translator import GoogleTranslator
from PIL import ImageFont


class XSelect:
    def __init__(self, display):
        # X display
        self.d = display

        # Screen
        self.screen = self.d.screen()

        # Draw on the root window (desktop surface)
        self.window = self.screen.root

        # Create font cursor
        font = display.open_font('cursor')
        self.cursor = font.create_glyph_cursor(
            font,
            Xcursorfont.crosshair,
            Xcursorfont.crosshair+1,
            (65535, 65535, 65535),
            (0, 0, 0)
        )

        colormap = self.screen.default_colormap
        color = colormap.alloc_color(0, 0, 0)
        # Xor it because we'll draw with X.GXxor function
        xor_color = color.pixel ^ 0xffffff

        self.gc = self.window.create_gc(
            line_width = 1,
            line_style = X.LineSolid,
            fill_style = X.FillOpaqueStippled,
            fill_rule  = X.WindingRule,
            cap_style  = X.CapButt,
            join_style = X.JoinMiter,
            foreground = xor_color,
            background = self.screen.black_pixel,
            function = X.GXxor,
            graphics_exposures = False,
            subwindow_mode = X.IncludeInferiors,
        )

    def get_mouse_selection(self):
        started = False
        start = dict(x=0, y=0)
        end = dict(x=0, y=0)
        last = None
        drawlimit = 10
        i = 0

        self.window.grab_pointer(
            self.d,
            X.PointerMotionMask|X.ButtonReleaseMask|X.ButtonPressMask,
            X.GrabModeAsync,
            X.GrabModeAsync,
            X.NONE,
            self.cursor,
            X.CurrentTime
        )

        self.window.grab_keyboard(self.d,
            X.GrabModeAsync,
            X.GrabModeAsync,
            X.CurrentTime
        )

        while True:
            e = self.d.next_event()

            # Window has been destroyed, quit
            if e.type == X.DestroyNotify:
                break

            # Mouse button press
            elif e.type == X.ButtonPress:
                # Left mouse button?
                if e.detail == 1:
                    start = dict(x=e.root_x, y=e.root_y)
                    started = True

                # Right mouse button?
                elif e.detail == 3:
                    return

            # Mouse button release
            elif e.type == X.ButtonRelease:
                end = dict(x=e.root_x, y=e.root_y)
                if last:
                    self.draw_rectangle(start, last)
                break

            # Mouse movement
            elif e.type == X.MotionNotify and started:
                i = i + 1
                if i % drawlimit != 0:
                    continue

                if last:
                    self.draw_rectangle(start, last)
                    last = None

                last = dict(x=e.root_x, y=e.root_y)
                self.draw_rectangle(start, last)

        self.d.ungrab_keyboard(X.CurrentTime)
        self.d.ungrab_pointer(X.CurrentTime)
        self.d.sync()

        coords = self.get_coords(start, end)
        if coords['width'] <= 1 or coords['height'] <= 1:
            return

        return [
            coords['start']['x'],
            coords['start']['y'],
            coords['width'],
            coords['height']
        ]

    def get_coords(self, start, end):
        safe_start = dict(x=0, y=0)
        safe_end   = dict(x=0, y=0)

        if start['x'] > end['x']:
            safe_start['x'] = end['x']
            safe_end['x']   = start['x']
        else:
            safe_start['x'] = start['x']
            safe_end['x']   = end['x']

        if start['y'] > end['y']:
            safe_start['y'] = end['y']
            safe_end['y']   = start['y']
        else:
            safe_start['y'] = start['y']
            safe_end['y']   = end['y']

        return {
            'start': {
                'x': safe_start['x'],
                'y': safe_start['y'],
            },
            'end': {
                'x': safe_end['x'],
                'y': safe_end['y'],
            },
            'width' : safe_end['x'] - safe_start['x'],
            'height': safe_end['y'] - safe_start['y'],
        }

    def draw_rectangle(self, start, end):
        coords = self.get_coords(start, end)
        self.window.rectangle(self.gc,
            coords['start']['x'],
            coords['start']['y'],
            coords['end']['x'] - coords['start']['x'],
            coords['end']['y'] - coords['start']['y']
        )


class Screenshot(QWidget):
    def __init__(self):
        super(Screenshot, self).__init__()

        self.screenshotLabel = QLabel()
        self.screenshotLabel.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self.screenshotLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.screenshotLabel.setMinimumSize(240, 160)

        self.createOptionsGroupBox()
        self.createButtonsLayout()

        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.screenshotLabel)
        mainLayout.addWidget(self.optionsGroupBox)
        mainLayout.addLayout(self.buttonsLayout)
        self.setLayout(mainLayout)

        self.area = None
        self.shootScreen()
        self.delaySpinBox.setValue(1)

        self.setWindowTitle("Screenshot")
        self.resize(300, 200)

    def resizeEvent(self, event):
        scaledSize = self.originalPixmap.size()
        scaledSize.scale(
            self.screenshotLabel.size(),
            QtCore.Qt.KeepAspectRatio
        )
        if not self.screenshotLabel.pixmap() \
        or scaledSize != self.screenshotLabel.pixmap().size():
            self.updateScreenshotLabel()

    def selectArea(self):
        self.hide()

        xs = XSelect(display.Display())
        self.area = xs.get_mouse_selection()

        if self.area:
            xo, yo, x, y = self.area
            self.areaLabel.setText(
                "Area: x%s y%s to x%s y%s" % (xo, yo, x, y)
            )
            self.shootScreen()
        else:
            self.areaLabel.setText("Area: fullscreen")
            self.shootScreen()

        self.show()

    def newScreenshot(self):
        if self.hideThisWindowCheckBox.isChecked():
            self.hide()
        self.newScreenshotButton.setDisabled(True)

        QtCore.QTimer.singleShot(
            self.delaySpinBox.value() * 1000,
            self.shootScreen
        )

    def saveScreenshot(self):
        format = 'png'
        initialPath = "./original." #QtCore.QDir.currentPath() + "/untitled." + format

        fileName, fileSuffixSelection = QFileDialog.getSaveFileName(
            self,
            "Save As",
            initialPath,
            "{} Files (*.{});;All Files (*)".format(
                format.upper(),
                format
            )
        )

        if fileName:
                self.originalPixmap.save(str(fileName), format)

    def copyToClipboard(self):
        if not self.originalPixmap:
            return
        qi = self.originalPixmap.toImage()
        QApplication.clipboard().setImage(qi)

    def translate(self):
        self.originalPixmap.save("./original.png")
        print("translate")
        image=cv2.imread("original.png")
        LANGUAGE = "ko"
        reader = easyocr.Reader([LANGUAGE])
        result = reader.readtext(image)
        print("read image")
        img_rect = cv2.imread("original.png") #cv2.imread(image)
        img_temp = cv2.imread("original.png") #cv2.imread(image)
        h, w, c = img_temp.shape

        img_temp = cv2.rectangle(img_temp, [0,0], [w, h], (0, 0, 0), -1)
        img_inpaint = cv2.imread("original.png")
        preview_rect = cv2.imread("original.png")

        raw_list = []
        rects = []
        print("before for loop")
        for r in result:
            raw_list.append(r[1])
            bottom_left = tuple(int(x) for x in tuple(r[0][0]))
            top_right = tuple(int(x) for x in tuple(r[0][2]))
            rects.append((top_right, bottom_left))
            # Draw a rectangle around the text
            img_rect = cv2.rectangle(img_rect, bottom_left, top_right, (0,255,0), 3)
            # Fill text with white rectangle
            img_temp = cv2.rectangle(img_temp, bottom_left, top_right, (255, 255, 255), -1)
            # Convert temp image to black and white for mask
            mask = cv2.cvtColor(img_temp, cv2.COLOR_BGR2GRAY)
            #cv2.imwrite("./mask.png", mask)
            # "Content-Fill" using mask (INPAINT_NS vs INPAINT_TELEA)
            print("img inpaint")
            img_inpaint = cv2.inpaint(img_inpaint, mask, 3, cv2.INPAINT_TELEA)
            #cv2.imwrite("./inpaint.png", img_inpaint)
            # Draw a rectangle around the text
            preview_rect = cv2.rectangle(img_rect, bottom_left, top_right, (0,255,0), 3)
            # Draw confidence level on detected text
            print("put text")
            cv2.putText(preview_rect, str(round(r[2], 2)), bottom_left, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, 1)
            #cv2.imwrite("./rect.png", preview_rect)

        threshold = 0.25
        print("translate")
        for t_, t in enumerate(result):
            bbox, text, score = t
            translated = GoogleTranslator(source='ko', target='en').translate(text)
            if score > threshold:
                cv2.putText(img_inpaint, translated, bbox[0], cv2.FONT_HERSHEY_COMPLEX, 1.0, (0, 0, 0), 2)
        cv2.imwrite("./translated.png", img_inpaint)
        print("finsihed")
        self.display()


    def convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.disply_width, self.display_height, Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)

    def display(self):
        print("display translated image")
        self.disply_width = 640
        self.display_height = 480
        cv_img = cv2.imread('translated.png')
        qt_img = self.convert_cv_qt(cv_img)
        self.originalPixmap = qt_img
        self.updateScreenshotLabel()

    def shootScreen(self):
        if self.delaySpinBox.value() != 0:
            QApplication.beep()

        # Garbage collect any existing image first.
        self.originalPixmap = None
        screen = QApplication.primaryScreen()
        self.originalPixmap = screen.grabWindow(
            QApplication.desktop().winId()
        )
        if self.area is not None:
            qi = self.originalPixmap.toImage()
            qi = qi.copy(
                int(self.area[0]),
                int(self.area[1]),
                int(self.area[2]),
                int(self.area[3])
            )
            self.originalPixmap = None
            self.originalPixmap = QPixmap.fromImage(qi)

        self.updateScreenshotLabel()

        self.newScreenshotButton.setDisabled(False)
        if self.hideThisWindowCheckBox.isChecked():
            self.show()

    def updateCheckBox(self):
        if self.delaySpinBox.value() == 0:
            self.hideThisWindowCheckBox.setDisabled(True)
        else:
            self.hideThisWindowCheckBox.setDisabled(False)

    def createOptionsGroupBox(self):
        self.optionsGroupBox = QGroupBox("Options")

        self.delaySpinBox = QSpinBox()
        self.delaySpinBox.setSuffix(" s")
        self.delaySpinBox.setMaximum(60)
        self.delaySpinBox.valueChanged.connect(self.updateCheckBox)

        self.delaySpinBoxLabel = QLabel("Screenshot Delay:")

        self.hideThisWindowCheckBox = QCheckBox("Hide This Window")
        self.hideThisWindowCheckBox.setChecked(True)

        self.areaLabel = QLabel("Area: fullscreen")

        optionsGroupBoxLayout = QGridLayout()
        optionsGroupBoxLayout.addWidget(self.delaySpinBoxLabel, 0, 0)
        optionsGroupBoxLayout.addWidget(self.delaySpinBox, 0, 1)
        optionsGroupBoxLayout.addWidget(
            self.hideThisWindowCheckBox,
            1,
            0
        )
        optionsGroupBoxLayout.addWidget(self.areaLabel, 1, 1)
        self.optionsGroupBox.setLayout(optionsGroupBoxLayout)

    def createButtonsLayout(self):
        self.selectAreaButton = self.createButton(
            "Select Area",
            self.selectArea
        )

        self.newScreenshotButton = self.createButton(
            "New Screenshot",
            self.newScreenshot
        )

        self.translateButton = self.createButton(
            "Translate",
            self.translate
        )

        self.saveScreenshotButton = self.createButton(
            "Save Screenshot",
            self.saveScreenshot
        )

        self.quitScreenshotButton = self.createButton(
            "Quit",
            self.close
        )

        self.buttonsLayout = QHBoxLayout()
        self.buttonsLayout.addStretch()
        self.buttonsLayout.addWidget(self.selectAreaButton)
        self.buttonsLayout.addWidget(self.newScreenshotButton)
        self.buttonsLayout.addWidget(self.translateButton)
        self.buttonsLayout.addWidget(self.saveScreenshotButton)
        self.buttonsLayout.addWidget(self.quitScreenshotButton)

    def createButton(self, text, member):
        button = QPushButton(text)
        button.clicked.connect(member)
        return button

    def updateScreenshotLabel(self):
        self.screenshotLabel.setPixmap(
            self.originalPixmap.scaled(
                self.screenshotLabel.size(), QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
        )


if __name__ == '__main__':
    app = QApplication(sys.argv)
    screenshot = Screenshot()
    screenshot.show()
    sys.exit(app.exec_())
