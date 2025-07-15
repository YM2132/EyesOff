from PyQt5.QtCore import Qt, QRect, QRectF, QPoint, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPainter, QPainterPath, QBrush, QPen
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QWidget, QGraphicsDropShadowEffect)

from .help_content import MAIN_WINDOW_STEPS

class WalkthroughDialog(QDialog):
    """Interactive walkthrough dialog for the main window."""
    
    walkthrough_finished = pyqtSignal()
    
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.steps = MAIN_WINDOW_STEPS
        self.current_step = 0
        self.highlight_rect = None

        # Colour scheme
        self.HIGHLIGHT_COLOR = QColor(233, 30, 99)  # Material Pink
        self.HIGHLIGHT_GLOW = QColor(255, 64, 129)  # Lighter pink for glow
        self.OVERLAY_COLOR = QColor(0, 0, 0, 150)  # Lighter overlay
        self.BUBBLE_BORDER = QColor(233, 30, 99)  # Match highlight
        
        # Setup dialog
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        
        # Set geometry to match main window immediately
        self.resize(main_window.size())
        self.move(main_window.mapToGlobal(QPoint(0, 0)))
        
        # Create help bubble
        self.help_bubble = self._create_help_bubble()
        
        # Start walkthrough
        self._show_step(0)
        
    def _create_help_bubble(self):
        """Create the help bubble widget."""
        bubble = QWidget(self)
        bubble.setObjectName("helpBubble")
        bubble.setStyleSheet(f"""
            #helpBubble {{
                background-color: white;
                border: 3px solid {self.BUBBLE_BORDER.name()};
                border-radius: 10px;
                padding: 20px;
            }}
        """)

        # Bubble layout
        layout = QVBoxLayout(bubble)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title label
        self.title_label = QLabel()
        self.title_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("color: #333;")
        layout.addWidget(self.title_label)
        
        # Description label
        self.desc_label = QLabel()
        self.desc_label.setFont(QFont("Arial", 12))
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #666; margin-top: 10px; margin-bottom: 20px;")
        layout.addWidget(self.desc_label)
        
        # Navigation buttons
        nav_layout = QHBoxLayout()

        self.skip_button = QPushButton("Skip Tour")
        self.skip_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.9);
                border: 2px solid #E91E63;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
                color: #E91E63;
            }
            QPushButton:hover {
                background-color: #E91E63;
                color: white;
            }
        """)
        self.skip_button.clicked.connect(self._finish_walkthrough)
        nav_layout.addWidget(self.skip_button)
        
        nav_layout.addStretch()

        self.prev_button = QPushButton("Previous")
        self.prev_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.9);
                border: 2px solid #757575;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
                color: #424242;
            }
            QPushButton:hover:enabled {
                background-color: #F5F5F5;
                border-color: #E91E63;
                color: #E91E63;
            }
            QPushButton:disabled {
                background-color: rgba(224, 224, 224, 0.6);
                color: #BDBDBD;
                border-color: #E0E0E0;
            }
        """)
        self.prev_button.clicked.connect(self._previous_step)
        nav_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Next")
        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #E91E63;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 14px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D81B60;
            }
            QPushButton:pressed {
                background-color: #C2185B;
            }
        """)
        self.next_button.clicked.connect(self._next_step)
        self.next_button.setDefault(True)
        nav_layout.addWidget(self.next_button)
        
        layout.addLayout(nav_layout)
        
        # Set fixed width
        bubble.setFixedWidth(400)
        bubble.adjustSize()
        
        return bubble
        
    def _show_step(self, step_index):
        """Show a specific step in the walkthrough."""
        if step_index < 0 or step_index >= len(self.steps):
            return
            
        self.current_step = step_index
        step = self.steps[step_index]
        
        # Update content
        self.title_label.setText(step.title)
        self.desc_label.setText(step.description)
        
        # Update navigation buttons
        self.prev_button.setEnabled(step_index > 0)
        
        if step_index == len(self.steps) - 1:
            self.next_button.setText("Finish")
        else:
            self.next_button.setText("Next")
        
        # Update step counter in title
        self.setWindowTitle(f"Help - Step {step_index + 1} of {len(self.steps)}")
        
        # Highlight the relevant widget
        if step.highlight_widget:
            widget = self._get_widget_by_path(step.highlight_widget)
            if widget and widget.isVisible():
                # Get global position and size
                rect = QRect(
                    widget.mapToGlobal(QPoint(0, 0)),
                    widget.size()
                )
                # Convert to dialog coordinates
                rect.moveTopLeft(self.mapFromGlobal(rect.topLeft()))
                
                # Add padding
                rect.adjust(-10, -10, 10, 10)
                
                self.highlight_rect = rect
                self._position_bubble(rect, step.position)
            else:
                self.highlight_rect = None
                self._position_bubble(None, "center")
        else:
            self.highlight_rect = None
            self._position_bubble(None, "center")
            
        # Force repaint
        self.update()
            
    def _get_widget_by_path(self, path: str):
        """Get a widget by its attribute path (e.g., 'webcam_view.webcam_label')."""
        parts = path.split('.')
        obj = self.main_window
        
        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return None
                
        return obj
        
    def _position_bubble(self, highlight_rect, position: str):
        """Position the help bubble relative to highlighted area."""
        # Ensure bubble size is calculated
        self.help_bubble.adjustSize()
        bubble_width = self.help_bubble.width()
        bubble_height = self.help_bubble.height()
        
        if highlight_rect is None or position == "center":
            # Center on screen
            x = (self.width() - bubble_width) // 2
            y = (self.height() - bubble_height) // 2
        else:
            # Position relative to highlight
            if position == "top":
                x = highlight_rect.center().x() - bubble_width // 2
                y = highlight_rect.top() - bubble_height - 20
            elif position == "bottom":
                x = highlight_rect.center().x() - bubble_width // 2
                y = highlight_rect.bottom() + 20
            elif position == "left":
                x = highlight_rect.left() - bubble_width - 20
                y = highlight_rect.center().y() - bubble_height // 2
            elif position == "right":
                x = highlight_rect.right() + 20
                y = highlight_rect.center().y() - bubble_height // 2
            elif position == "top-left":
                x = highlight_rect.left()
                y = highlight_rect.top() - bubble_height - 20
            elif position == "top-right":
                x = highlight_rect.right() - bubble_width
                y = highlight_rect.top() - bubble_height - 20
            else:  # Default to bottom
                x = highlight_rect.center().x() - bubble_width // 2
                y = highlight_rect.bottom() + 20
                
            # Keep bubble on screen
            x = max(10, min(x, self.width() - bubble_width - 10))
            y = max(10, min(y, self.height() - bubble_height - 10))
            
        # Move the bubble
        self.help_bubble.move(x, y)
        
    def _next_step(self):
        """Go to next step."""
        if self.current_step < len(self.steps) - 1:
            self._show_step(self.current_step + 1)
        else:
            self._finish_walkthrough()
            
    def _previous_step(self):
        """Go to previous step."""
        if self.current_step > 0:
            self._show_step(self.current_step - 1)
            
    def _finish_walkthrough(self):
        """Finish the walkthrough."""
        self.walkthrough_finished.emit()
        self.accept()
        
    def paintEvent(self, event):
        """Paint the overlay."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get the full rect of the dialog
        full_rect = self.rect()

        # First, always fill the entire area with overlay
        painter.fillRect(full_rect, self.OVERLAY_COLOR)
        
        if self.highlight_rect:
            # Create a path for the highlight area
            highlight_path = QPainterPath()
            highlight_path.addRoundedRect(QRectF(self.highlight_rect), 10, 10)

            # Clear the highlight area (make it transparent)
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            painter.fillPath(highlight_path, QBrush())

            # Reset composition mode for border drawing
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            # Draw border
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(self.HIGHLIGHT_COLOR, 3))
            painter.drawRoundedRect(self.highlight_rect, 10, 10)

        else:
            # Dim entire screen
            painter.fillRect(full_rect, self.OVERLAY_COLOR)

    def showEvent(self, event):
        """Ensure dialog covers the main window."""
        super().showEvent(event)
        
        # Get the main window's position and size in global coordinates
        main_pos = self.main_window.mapToGlobal(QPoint(0, 0))
        main_size = self.main_window.size()
        
        # Set the dialog to exactly cover the main window
        self.move(main_pos)
        self.resize(main_size)
        
        # Show and position help bubble
        self.help_bubble.show()
        self.help_bubble.raise_()
        
        # Re-show current step to position bubble correctly
        QTimer.singleShot(100, lambda: self._show_step(self.current_step))
        
    def keyPressEvent(self, event):
        """Handle keyboard navigation."""
        if event.key() == Qt.Key_Escape:
            self._finish_walkthrough()
        elif event.key() == Qt.Key_Right:
            self._next_step()
        elif event.key() == Qt.Key_Left:
            self._previous_step()
            
    def mousePressEvent(self, event):
        """Handle mouse clicks."""
        # Check if click is outside the highlight area
        if self.highlight_rect and not self.highlight_rect.contains(event.pos()):
            # Check if click is on the help bubble
            bubble_rect = QRect(self.help_bubble.pos(), self.help_bubble.size())
            if not bubble_rect.contains(event.pos()):
                # Click is outside both highlight and bubble - could skip to next step
                pass
