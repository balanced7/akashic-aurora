"""arsenal.media.league -- League of Legends footage: the HUD, the game clock, Riot's match record, events on frames.

    hud     named HUD boxes as fractions of the frame (hud_boxes.json), detect_layout(frame) -> replay | live | none
    clock   HUD clock OCR -> studio.clockmap.v1 (file_t <-> game_t per replay pass), to_game / to_file
    live    Live Client Data poller beside an OBS recording -> an exact clockmap with no OCR
    riot    cached match-v5 + timeline, typed events, roleBoundItem builds, mm:ss
    events  Riot events x clockmap -> every file time that shows them; fights

Game times are game_t and file times file_t everywhere; nothing here calls Riot's web API. Imports stay lazy.
"""
