class WalkthroughStep:
    def __init__(self, 
                 title: str,
                 description: str,
                 highlight_widget: str,  # Widget attribute name to highlight
                 position: str = "center",  # Position of help bubble
                 arrow_direction: str = "none"):
        self.title = title
        self.description = description
        self.highlight_widget = highlight_widget
        self.position = position
        self.arrow_direction = arrow_direction

# Define walkthrough steps
MAIN_WINDOW_STEPS = [
    WalkthroughStep(
        title="Welcome to EyesOff Privacy Monitor",
        description="EyesOff protects your privacy by detecting when someone is looking at your screen. Let's take a quick tour of the main features.",
        highlight_widget=None,
        position="center"
    ),
    WalkthroughStep(
        title="Live Camera Feed",
        description="This area shows your webcam feed in real-time. When monitoring is active, you'll see colored boxes around detected faces.",
        highlight_widget="webcam_view.webcam_label",
        position="center",
        arrow_direction="center"
    ),
    WalkthroughStep(
        title="Face Detection Box",
        description="Boxes will appear around detected faces. The color indicates whether someone is looking at your screen:\n• Green: Not looking at screen\n• Red/Orange: Looking at screen",
        highlight_widget="webcam_view.webcam_label",
        position="bottom",
        arrow_direction="up"
    ),
    WalkthroughStep(
        title="Face Counter",
        description="Shows the number of faces currently detected and the number of people currently looking at your screen. When this exceeds your threshold (default: 1), a privacy alert will trigger.",
        highlight_widget="webcam_view.webcam_label",
        position="top-right",
        arrow_direction="top-right"
    ),
    WalkthroughStep(
        title="Gaze Detection Score",
        description="The 'Looking' score (0.00-1.00) indicates how likely someone is looking at your screen. Higher values mean they're more likely looking directly at your display.",
        highlight_widget="webcam_view.webcam_label",
        position="right",
        arrow_direction="left"
    ),
    WalkthroughStep(
        title="Start/Stop Monitoring",
        description="Click this button to start or stop privacy monitoring. When stopped, no face detection or alerts will occur.",
        highlight_widget="webcam_view.toggle_button",
        position="top",
        arrow_direction="down"
    ),
    WalkthroughStep(
        title="Snapshot Feature",
        description="Take a snapshot of the current view, including detection boxes. Useful for reviewing who triggered alerts. Snapshots are saved to your configured directory.",
        highlight_widget="webcam_view.snapshot_button",
        position="top",
        arrow_direction="down"
    ),
    WalkthroughStep(
        title="Status Bar",
        description="Shows important information:\n• Alerts: Number of privacy alerts triggered\n• Session: How long monitoring has been active",
        highlight_widget="statusBar",
        position="top",
        arrow_direction="down"
    ),
    WalkthroughStep(
        title="You're Ready!",
        description="That's it! You can access Settings from the Edit menu to customize detection sensitivity, alerts, and more. Now it's time for EyesOff to start protecting your privacy!",
        highlight_widget=None,
        position="center"
    )
]