// LaunchPad.m - Simplified with proper Sparkle behavior
#import <Cocoa/Cocoa.h>
#import <Sparkle/SPUStandardUpdaterController.h>
#import <Sparkle/SPUUpdater.h>

@interface LauncherDelegate : NSObject <NSApplicationDelegate>
@property (strong) SPUStandardUpdaterController *updaterController;
@property (strong) NSTask *pythonTask;
@end

@implementation LauncherDelegate

- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    // Initialize Sparkle
    @try {
        self.updaterController = [[SPUStandardUpdaterController alloc]
            initWithStartingUpdater:YES
            updaterDelegate:nil
            userDriverDelegate:nil];
        NSLog(@"LaunchPad: Sparkle initialized successfully");

        // Listen for update check requests from Python
        [[NSDistributedNotificationCenter defaultCenter]
		    addObserver:self
		    selector:@selector(checkForUpdatesManually)
		    name:@"app.eyesoff.checkForUpdatesManually"
		    object:nil
		    suspensionBehavior:NSNotificationSuspensionBehaviorDeliverImmediately];

		// Listen for auto-update setting changes
	    [[NSDistributedNotificationCenter defaultCenter]
	        addObserver:self
	        selector:@selector(setAutomaticUpdates:)
	        name:@"app.eyesoff.setAutomaticUpdates"
	        object:nil
	        suspensionBehavior:NSNotificationSuspensionBehaviorDeliverImmediately];

		NSLog(@"LaunchPad: Listening for updates notification");

    } @catch (NSException *exception) {
        NSLog(@"LaunchPad: Failed to initialize Sparkle: %@", exception);
    }

    // Launch Python app immediately
    [self launchPythonApp];
}

- (void)checkForUpdatesManually {
    NSLog(@"LaunchPad: Manual update check triggered!");

    // Check if the updater is ready
    SPUUpdater *updater = self.updaterController.updater;
    NSLog(@"Updater: %@", updater);
    NSLog(@"Can check for updates: %@", updater.canCheckForUpdates ? @"YES" : @"NO");

    if (!updater.canCheckForUpdates) {
        NSLog(@"WARNING: Updater says it cannot check for updates!");
        NSLog(@"automaticallyChecksForUpdates: %@", updater.automaticallyChecksForUpdates ? @"YES" : @"NO");
        NSLog(@"updateInProgress: %@", updater.sessionInProgress ? @"YES" : @"NO");
    }

    // Call it anyway
    [self.updaterController checkForUpdates:self];
}

// Handler to set automatic updates
- (void)setAutomaticUpdates:(NSNotification *)notification {
    NSDictionary *userInfo = notification.userInfo;
    BOOL enabled = [[userInfo objectForKey:@"enabled"] boolValue];

    NSLog(@"LaunchPad: Setting automatic updates to: %@", enabled ? @"YES" : @"NO");

    SPUUpdater *updater = self.updaterController.updater;
    [updater setAutomaticallyChecksForUpdates:enabled];

    // Report back the new state
    [self reportAutomaticUpdatesState];
}

// Handler to report current state
- (void)reportAutomaticUpdatesState {
    SPUUpdater *updater = self.updaterController.updater;
    BOOL autoChecks = updater.automaticallyChecksForUpdates;

    NSLog(@"LaunchPad: Reporting automatic updates state: %@", autoChecks ? @"YES" : @"NO");

    [[NSDistributedNotificationCenter defaultCenter]
        postNotificationName:@"app.eyesoff.automaticUpdatesState"
        object:nil
        userInfo:@{@"enabled": @(autoChecks)}
        deliverImmediately:YES];
}

- (void)launchPythonApp {
    NSBundle *mainBundle = [NSBundle mainBundle];
    NSString *macOSDir = [[mainBundle executablePath] stringByDeletingLastPathComponent];
    NSString *pythonPath = [macOSDir stringByAppendingPathComponent:@"EyesOffPython"];

    NSLog(@"LaunchPad: Looking for Python app at: %@", pythonPath);

    NSFileManager *fm = [NSFileManager defaultManager];
    if (![fm fileExistsAtPath:pythonPath]) {
        NSLog(@"Error: Could not find EyesOffPython at %@", pythonPath);

        NSAlert *alert = [[NSAlert alloc] init];
        [alert setMessageText:@"Application Error"];
        [alert setInformativeText:@"Could not find the main application executable."];
        [alert addButtonWithTitle:@"OK"];
        [alert runModal];

        [[NSApplication sharedApplication] terminate:nil];
        return;
    }

    // Launch Python as child process
    self.pythonTask = [[NSTask alloc] init];
    [self.pythonTask setLaunchPath:pythonPath];

    // Forward arguments and environment
    NSArray *args = [[NSProcessInfo processInfo] arguments];
    if (args.count > 1) {
        [self.pythonTask setArguments:[args subarrayWithRange:NSMakeRange(1, args.count - 1)]];
    }
    [self.pythonTask setEnvironment:[[NSProcessInfo processInfo] environment]];

    // Set up termination handler
    self.pythonTask.terminationHandler = ^(NSTask *task) {
        dispatch_async(dispatch_get_main_queue(), ^{
            NSLog(@"Python app terminated with status: %d", task.terminationStatus);
            [[NSApplication sharedApplication] terminate:nil];
        });
    };

    @try {
        [self.pythonTask launch];
        NSLog(@"LaunchPad: Python app launched successfully");
    } @catch (NSException *exception) {
        NSLog(@"Error launching Python app: %@", exception);

        NSAlert *alert = [[NSAlert alloc] init];
        [alert setMessageText:@"Launch Error"];
        [alert setInformativeText:[NSString stringWithFormat:@"Failed to launch application: %@", exception.reason]];
        [alert addButtonWithTitle:@"OK"];
        [alert runModal];

        [[NSApplication sharedApplication] terminate:nil];
    }
}

- (void)applicationWillTerminate:(NSNotification *)notification {
    if (self.pythonTask && [self.pythonTask isRunning]) {
        NSLog(@"LaunchPad: Terminating Python process");
        [self.pythonTask terminate];
    }
}

- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {
    return NO;
}

@end

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSApplication *app = [NSApplication sharedApplication];
        LauncherDelegate *delegate = [[LauncherDelegate alloc] init];
        [app setDelegate:delegate];
        [app setActivationPolicy:NSApplicationActivationPolicyAccessory];
        [app run];
        return 0;
    }
}