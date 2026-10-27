// See DataBookmark.h for why this exists.

#import "DataBookmark.h"

static NSString *const kPickedData = @"pickedDataBookmark";

NSData *dm_picked_data_bookmark(void) {
    return [NSUserDefaults.standardUserDefaults dataForKey:kPickedData];
}

NSString *dm_picked_data_path(BOOL *stale) {
    if (stale) *stale = NO;
    NSData *bookmark = dm_picked_data_bookmark();
    if (bookmark.length == 0) return nil;
    BOOL isStale = NO;
    NSError *error = nil;
    NSURL *url = [NSURL URLByResolvingBookmarkData:bookmark
                                           options:0
                                     relativeToURL:nil
                               bookmarkDataIsStale:&isStale
                                             error:&error];
    if (isStale && stale) *stale = YES;
    if (!url) {
        // A re-signed build gets a bookmark the system will not resolve for it. Keep the data —
        // the player may install the same signature again — and let the caller ask for a new pick.
        fprintf(stderr, "boot: the picked game-data bookmark does not resolve (%s)\n",
                error.localizedDescription.UTF8String ?: "no reason given");
        if (stale) *stale = YES;
        return nil;
    }
    // The picker can hand back a file that was moved or deleted since. The caller checks what it
    // needs (an image, a folder with the marker) and falls through if this path no longer holds it.
    return url.path;
}

BOOL dm_store_picked_data(NSURL *url) {
    NSError *error = nil;
    NSData *bookmark = [url bookmarkDataWithOptions:0 includingResourceValuesForKeys:nil relativeToURL:nil error:&error];
    if (!bookmark) {
        fprintf(stderr, "[RED] could not bookmark %s: %s\n", url.path.UTF8String ?: "?",
                error.localizedDescription.UTF8String ?: "no reason given");
        return NO;
    }
    [NSUserDefaults.standardUserDefaults setObject:bookmark forKey:kPickedData];
    fprintf(stderr, "launcher: game data set to %s\n", url.path.UTF8String ?: "?");
    return YES;
}

void dm_clear_picked_data(void) {
    [NSUserDefaults.standardUserDefaults removeObjectForKey:kPickedData];
}
