// LaunchPad.m - Simplified with proper Sparkle behavior
#import <Cocoa/Cocoa.h>
#import <Sparkle/SPUStandardUpdaterController.h>

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

        // DON'T call checkForUpdates here - let Sparkle handle it automatically
        // based on SUScheduledCheckInterval in Info.plist

    } @catch (NSException *exception) {
        NSLog(@"LaunchPad: Failed to initialize Sparkle: %@", exception);
    }

    // Launch Python app immediately
    [self launchPythonApp];
}

- (void)checkForUpdatesManually {
    // This method can be called when user clicks "Check for Updates" menu item
    [self.updaterController checkForUpdates:nil];
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