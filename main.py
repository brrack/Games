import pygame, random, math
pygame.init()

# ---------------- CONFIG ----------------
FPS = 60
WIDTH, HEIGHT = 1075, 800
SCALE = 0.3
BG = (0, 60, 0)
SNAP_RADIUS = 150  # pixels
DEFAULT_INACTIVITY_SECONDS = 2.5  # default timeout (adjustable)
# ----------------------------------------

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Speed")

# load cardback and scale
cardback = pygame.image.load("card sprites/cardback.png").convert_alpha()
w, h = cardback.get_size()
cardback = pygame.transform.smoothscale(cardback, (int(w * SCALE), int(h * SCALE)))

# load all card faces (filenames expected to be like 'ace_of_spades.png', '2_of_spades.png', etc.)
cards = {}
suits = ["spades", "clubs", "diamonds", "hearts"]
values = ["ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "jack", "queen", "king"]
# create keys like "1_of_spades", "11_of_hearts", etc. to match your earlier code
for suit in suits:
    for i, val in enumerate(values, start=1):
        key = f"{i}_of_{suit}"
        path = f"card sprites/{val}_of_{suit}.png"
        img = pygame.image.load(path).convert_alpha()
        w, h = img.get_size()
        cards[key] = pygame.transform.smoothscale(img, (int(w * SCALE), int(h * SCALE)))

# positions (index comments for clarity)
cardPos = [
    (350, 285),     # 0 play left
    (550, 285),     # 1 play right
    (150, 285),     # 2 center back right (pile)
    (750, 285),     # 3 center back left (pile)
    (25, 555),      # 4 player hand 1
    (200, 555),     # 5 player hand 2
    (375, 555),     # 6 player hand 3
    (550, 555),     # 7 player hand 4
    (725, 555),     # 8 player hand 5
    (900, 555),     # 9 player draw pile (back)
    (25, 25),       # 10 bot hand 1
    (200, 25),      # 11 bot hand 2
    (375, 25),      # 12 bot hand 3
    (550, 25),      # 13 bot hand 4
    (725, 25),      # 14 bot hand 5
    (900, 25)       # 15 bot draw pile (back)
]

# pile sizes for back positions
pile_sizes = {2: 5, 3: 5, 9: 15, 15: 15}
deck_piles = {}       # position index -> list of card names
used_cards = set()    # names already used on board or in piles

def getCardNum(card_key):
    # card_key format: "1_of_spades", "11_of_hearts", etc.
    base = card_key.split("_")[0]
    try:
        return int(base)
    except:
        return 0

# prepare sprite containers
placed_sprites = []
back_positions = [2, 3, 9, 15]
PlayCards = [cardPos[0], cardPos[1]]  # positions for center play (left and right)

# shuffle deck and create piles
all_card_names = list(cards.keys())
random.shuffle(all_card_names)
for pos_index, size in pile_sizes.items():
    pile = []
    for _ in range(size):
        if not all_card_names:
            break
        name = all_card_names.pop()
        pile.append(name)
        used_cards.add(name)
    deck_piles[pos_index] = pile

# create initial visible front cards and backs
sprite_names = list(cards.keys())
random.shuffle(sprite_names)
front_count = 0
cardset = []

for i, pos in enumerate(cardPos):
    if i in back_positions:
        rect = cardback.get_rect(topleft=pos)
        placed_sprites.append({
            "image": cardback,
            "rect": rect,
            "dragging": False,
            "draggable": False,
            "orig_pos": pos,
            "is_back": True,
            "pile_index": i
        })
    else:
        # take the next random sprite for initial layout (player and bot hands + center open slots)
        if not sprite_names:
            continue
        name = sprite_names.pop()
        rect = cards[name].get_rect(topleft=pos)
        # only first two front cards (the center play cards) are non-draggable; 
        # others: player hand positions (4-8) draggable, bot hand non-draggable for player
        draggable = (4 <= i <= 8)  # only player hand slots are draggable by player
        placed_sprites.append({
            "image": cards[name],
            "rect": rect,
            "dragging": False,
            "draggable": draggable,
            "orig_pos": pos,
            "name": name,
            "is_back": False,
            "number": getCardNum(name)
        })
        used_cards.add(name)
        # first two non-back placed are the center play cards for initial cardset
        cardset.append(getCardNum(name))
        front_count += 1

# ensure cardset has two values
if len(cardset) >= 2:
    cardset = [cardset[0], cardset[1]]
else:
    cardset = [1, 1]

# game state helpers
clock = pygame.time.Clock()
running = True

# dragging helpers and flags
dragging = False
dragged_sprite = None

# Bot timing & inactivity timeframe (set by difficulty screen later)
BOT_DELAY = 90
BOT_SMART = True
bot_timer = 0

# inactivity timer (frames) adjustable; default to provided seconds
INACTIVITY_THRESHOLD = int(DEFAULT_INACTIVITY_SECONDS * FPS)
inactivity_timer = 0

# ------------------ Helper functions ------------------

def remove_back_card(pos_index):
    """Remove the back sprite at pos_index if present (visual removal)."""
    pos = cardPos[pos_index]
    for s in placed_sprites[:]:
        if s.get("is_back") and s["rect"].topleft == pos:
            placed_sprites.remove(s)
            # also clear deck_piles entry to avoid future use
            deck_piles[pos_index] = []
            print(f"Removed back card at pile {pos_index}")
            break

def draw_new_cards():
    """When player clicks pile 9: fill empty player hand slots (4-8) from deck_piles[9]."""
    global placed_sprites, used_cards, deck_piles
    hand_positions = cardPos[4:9]
    empty_slots = [p for p in hand_positions if not any(s["rect"].topleft == p for s in placed_sprites if not s.get("is_back"))]
    if not empty_slots:
        return
    pile = deck_piles.get(9, [])
    if not pile:
        remove_back_card(9)
        print("Player draw pile empty.")
        return
    for pos in empty_slots:
        if not pile:
            remove_back_card(9)
            break
        name = pile.pop()
        used_cards.add(name)
        placed_sprites.append({
            "image": cards[name],
            "rect": cards[name].get_rect(topleft=pos),
            "dragging": False,
            "draggable": True,
            "orig_pos": pos,
            "name": name,
            "is_back": False,
            "number": getCardNum(name)
        })
        print(f"Drew {name} into {pos}")
    deck_piles[9] = pile
    if not pile:
        remove_back_card(9)

def refill_bot_hand(empty_pos):
    """Refill one bot hand position from pile 15. If empty_pos is None, fill first available."""
    global placed_sprites, deck_piles, used_cards
    pile = deck_piles.get(15, [])
    if not pile:
        remove_back_card(15)
        return
    if empty_pos is None:
        hand_positions = cardPos[10:15]
        used_positions = [s["rect"].topleft for s in placed_sprites if not s.get("is_back")]
        possibles = [p for p in hand_positions if p not in used_positions]
        if not possibles:
            return
        empty_pos = possibles[0]
    name = pile.pop()
    used_cards.add(name)
    placed_sprites.append({
        "image": cards[name],
        "rect": cards[name].get_rect(topleft=empty_pos),
        "dragging": False,
        "draggable": False,  # bot cards are not draggable by player
        "orig_pos": empty_pos,
        "name": name,
        "is_back": False,
        "number": getCardNum(name)
    })
    deck_piles[15] = pile
    if not pile:
        remove_back_card(15)

def bot_can_play(cardnum, center_num):
    """Return True if cardnum can be played on a center card value center_num."""
    return (abs(cardnum - center_num) == 1) or (cardnum == 13 and center_num == 1) or (cardnum == 1 and center_num == 13)

def get_current_center_values():
    """Read the actual current numbers of the two center play cards (prefer visible sprites)."""
    left_val, right_val = None, None
    for s in placed_sprites:
        if s["rect"].topleft == cardPos[0] and not s.get("is_back"):
            left_val = s["number"]
        if s["rect"].topleft == cardPos[1] and not s.get("is_back"):
            right_val = s["number"]
    if left_val is None: left_val = cardset[0]
    if right_val is None: right_val = cardset[1]
    return [left_val, right_val]

def bot_take_turn():
    """Bot attempts to play one valid card, else draws. Resets inactivity timer on a successful play."""
    global placed_sprites, cardset, deck_piles, inactivity_timer
    bot_hand_positions = cardPos[10:15]
    left_center_pos, right_center_pos = cardPos[0], cardPos[1]
    left_val, right_val = get_current_center_values()
    bot_hand = [s for s in placed_sprites if s["rect"].topleft in bot_hand_positions and not s.get("is_back")]
    random.shuffle(bot_hand)
    for s in bot_hand:
        num = s["number"]
        hand_pos = s["rect"].topleft
        if bot_can_play(num, left_val):
            # remove old center-left card (if any)
            for other in placed_sprites[:]:
                if other["rect"].topleft == left_center_pos and not other.get("is_back"):
                    placed_sprites.remove(other)
            s["rect"].topleft = left_center_pos
            s["draggable"] = False
            s["orig_pos"] = left_center_pos
            cardset[0] = num
            inactivity_timer = 0
            refill_bot_hand(hand_pos)
            print(f"Bot plays {s.get('name')} on LEFT -> {cardset}")
            return True
        if bot_can_play(num, right_val):
            for other in placed_sprites[:]:
                if other["rect"].topleft == right_center_pos and not other.get("is_back"):
                    placed_sprites.remove(other)
            s["rect"].topleft = right_center_pos
            s["draggable"] = False
            s["orig_pos"] = right_center_pos
            cardset[1] = num
            inactivity_timer = 0
            refill_bot_hand(hand_pos)
            print(f"Bot plays {s.get('name')} on RIGHT -> {cardset}")
            return True
    # nothing playable -> draw one card into bot hand
    pile = deck_piles.get(15, [])
    if pile:
        print("Bot cannot play, drawing...")
        refill_bot_hand(None)
    else:
        print("Bot pile empty.")
    return False

def isValidCard(card_name, dropped_pos):
    """Check if player's card can be placed onto dropped_pos (must be PlayCards[0] or PlayCards[1]).
       If valid, update cardset and reset inactivity timer."""
    global cardset, inactivity_timer
    cardnum = getCardNum(card_name)
    if dropped_pos == PlayCards[0]:
        side = "left"
        center_val = cardset[0]
    elif dropped_pos == PlayCards[1]:
        side = "right"
        center_val = cardset[1]
    else:
        return False
    valid = False
    if cardnum + 1 == center_val or cardnum - 1 == center_val:
        valid = True
    elif cardnum == 13 and center_val == 1:
        valid = True
    elif cardnum == 1 and center_val == 13:
        valid = True
    if not valid:
        return False
    # update center side and reset inactivity
    if side == "left":
        cardset[0] = cardnum
    else:
        cardset[1] = cardnum
    inactivity_timer = 0
    print(f"Valid play: {card_name} -> {side} -> {cardset}")
    return True

def flip_new_center_cards():
    """Flip top cards from deck_piles[2] and deck_piles[3] into the center (if both available).
       If either pile empties, both backs are removed."""
    global cardset, deck_piles, inactivity_timer
    pile2 = deck_piles.get(2, [])
    pile3 = deck_piles.get(3, [])
    if not pile2 or not pile3:
        # remove both backs if either empty
        remove_back_card(2)
        remove_back_card(3)
        print("Center piles empty -> backs removed.")
        return
    left_card = pile2.pop()
    right_card = pile3.pop()
    # remove current visual center cards (non-backs)
    for s in placed_sprites[:]:
        if s["rect"].topleft in [cardPos[0], cardPos[1]] and not s.get("is_back"):
            placed_sprites.remove(s)
    # add new center cards (non-draggable)
    for card_name, pos in zip([left_card, right_card], [cardPos[0], cardPos[1]]):
        placed_sprites.append({
            "image": cards[card_name],
            "rect": cards[card_name].get_rect(topleft=pos),
            "dragging": False,
            "draggable": False,
            "orig_pos": pos,
            "name": card_name,
            "is_back": False,
            "number": getCardNum(card_name)
        })
    cardset = [getCardNum(left_card), getCardNum(right_card)]
    inactivity_timer = 0
    print(f"Flipped new centers: {cardset}")
    # if either exhausted now -> remove both backs
    if not deck_piles.get(2) or not deck_piles.get(3):
        remove_back_card(2)
        remove_back_card(3)
        print("Center piles depleted after flip -> backs removed.")

def check_winner():
    """Return 'player' or 'bot' or None if no winner. Only call when not dragging."""
    player_hand_positions = cardPos[4:9]
    bot_hand_positions = cardPos[10:15]
    player_cards = [s for s in placed_sprites if s["rect"].topleft in player_hand_positions and not s.get("is_back")]
    bot_cards = [s for s in placed_sprites if s["rect"].topleft in bot_hand_positions and not s.get("is_back")]
    player_pile = deck_piles.get(9, [])
    bot_pile = deck_piles.get(15, [])
    if not player_cards and not player_pile:
        return "player"
    if not bot_cards and not bot_pile:
        return "bot"
    return None

def show_winner_screen(winner):
    """Display winner and wait for click to quit."""
    font = pygame.font.SysFont("arial", 72)
    small = pygame.font.SysFont("arial", 32)
    if winner == "player":
        text = "YOU WIN!"
        color = (0, 200, 0)
    else:
        text = "BOT WINS!"
        color = (200, 0, 0)
    screen.fill((0, 40, 0))
    title = font.render(text, True, color)
    rect = title.get_rect(center=(WIDTH//2, HEIGHT//2 - 40))
    screen.blit(title, rect)
    prompt = small.render("Click anywhere to quit", True, (255,255,255))
    screen.blit(prompt, prompt.get_rect(center=(WIDTH//2, HEIGHT//2 + 50)))
    pygame.display.flip()
    waiting = True
    while waiting:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                waiting = False
    pygame.quit(); exit()

# ---------------- difficulty selection screen ----------------
def choose_difficulty():
    font = pygame.font.SysFont("arial", 48)
    small = pygame.font.SysFont("arial", 28)
    title = font.render("Choose Bot Difficulty", True, (255,255,255))
    options = [
        {"label": "Easy", "rect": pygame.Rect(WIDTH//2 - 220, HEIGHT//2, 160, 64), "color": (0,120,0)},
        {"label": "Medium", "rect": pygame.Rect(WIDTH//2 - 20, HEIGHT//2, 160, 64), "color": (180,150,0)},
        {"label": "Hard", "rect": pygame.Rect(WIDTH//2 + 180, HEIGHT//2, 160, 64), "color": (150,0,0)}
    ]
    while True:
        screen.fill((0,40,0))
        screen.blit(title, title.get_rect(center=(WIDTH//2, HEIGHT//3)))
        for opt in options:
            pygame.draw.rect(screen, opt["color"], opt["rect"], border_radius=10)
            lbl = small.render(opt["label"], True, (255,255,255))
            screen.blit(lbl, lbl.get_rect(center=opt["rect"].center))
        pygame.display.flip()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                for opt in options:
                    if opt["rect"].collidepoint(ev.pos):
                        print("Difficulty:", opt["label"])
                        return opt["label"].lower()

difficulty = choose_difficulty()
if difficulty == "easy":
    BOT_DELAY = 180; BOT_SMART = False
elif difficulty == "medium":
    BOT_DELAY = 90; BOT_SMART = True
else:
    BOT_DELAY = 45; BOT_SMART = True

# Make inactivity threshold adjustable (default 2.5s)
INACTIVITY_THRESHOLD = int(DEFAULT_INACTIVITY_SECONDS * FPS)

# ---------------- MAIN LOOP ----------------
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # MOUSE DOWN: either start drag (player hand) or click back piles
        elif event.type == pygame.MOUSEBUTTONDOWN:
            for s in reversed(placed_sprites):
                if s["rect"].collidepoint(event.pos):
                    # if it's a back pile sprite
                    if s.get("is_back"):
                        pile_index = s.get("pile_index")
                        if pile_index in (2, 3):
                            flip_new_center_cards()
                            break
                        if pile_index == 9:
                            draw_new_cards()
                            break
                        if pile_index == 15:
                            # optionally trigger bot draw or ignore
                            break
                    # start dragging if this is a player's draggable card (only player hand slots are draggable)
                    if s.get("draggable"):
                        dragging = True
                        dragged_sprite = s
                        s["dragging"] = True
                        mx, my = event.pos
                        s["offset"] = (s["rect"].x - mx, s["rect"].y - my)
                        # bring to top visually
                        placed_sprites.append(placed_sprites.pop(placed_sprites.index(s)))
                        break

        # MOUSE UP: release any dragging sprite, try snap/placement
        elif event.type == pygame.MOUSEBUTTONUP:
            if dragged_sprite:
                # try to snap to closest PlayCard
                dragged_sprite["dragging"] = False
                sprite = dragged_sprite
                dragged_sprite = None
                dragging = False

                # compute closest center slot
                sprite_center = sprite["rect"].center
                closest_pos = None
                closest_dist = float("inf")
                for target_pos in PlayCards:
                    target_center = (target_pos[0] + sprite["rect"].width//2, target_pos[1] + sprite["rect"].height//2)
                    dist = math.hypot(sprite_center[0] - target_center[0], sprite_center[1] - target_center[1])
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_pos = target_pos

                snapped = False
                if closest_pos and closest_dist < SNAP_RADIUS:
                    # only accept if valid play on that specific side
                    if isValidCard(sprite["name"], closest_pos):
                        # remove any existing center card (non-back)
                        for other in placed_sprites[:]:
                            if other is not sprite and other["rect"].topleft == closest_pos and not other.get("is_back"):
                                placed_sprites.remove(other)
                        sprite["rect"].topleft = closest_pos
                        sprite["draggable"] = False  # lock it in center
                        snapped = True
                if not snapped:
                    # revert to original pos
                    sprite["rect"].topleft = sprite["orig_pos"]

    # update dragging positions while mouse held
    for s in placed_sprites:
        if s.get("dragging"):
            mx, my = pygame.mouse.get_pos()
            ox, oy = s.get("offset", (0,0))
            s["rect"].x = mx + ox
            s["rect"].y = my + oy

    # BOT turn timing
    bot_timer += 1
    if bot_timer >= BOT_DELAY:
        # BOT_SMART controls behavior: if false, bot sometimes skips attempts
        if BOT_SMART or random.random() < 0.5:
            bot_take_turn()
        bot_timer = 0

    # inactivity logic: increment only when not dragging
    if not dragging:
        inactivity_timer += 1
    # else do not increment inactivity while player is dragging last card (prevents false win)

    if inactivity_timer >= INACTIVITY_THRESHOLD:
        print("Inactivity threshold reached -> flipping new center cards")
        flip_new_center_cards()
        inactivity_timer = 0

    # draw
    screen.fill(BG)
    for s in placed_sprites:
        screen.blit(s["image"], s["rect"])

    # check winner only when not dragging (prevents false win when player picks up last card)
    if not dragging:
        winner = check_winner()
        if winner:
            show_winner_screen(winner)

    # debug idle display (optional)
    font = pygame.font.SysFont("arial", 20)
    timer_text = font.render(f"Idle: {inactivity_timer//FPS}s", True, (255,255,255))
    screen.blit(timer_text, (10, HEIGHT-30))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()