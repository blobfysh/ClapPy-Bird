from itertools import cycle
import random
import sys
import os
os.environ['SDL_VIDEO_WINDOW_POS'] = "0, 0"

import pygame
import pygame.locals
from threading import Thread
from micListener import get_current_note
from micListener import args

t = Thread(target=get_current_note)
t.daemon = True
t.start()

FPS = 30
SCREENWIDTH  = args.width if args.width else 1024 if args.res == 1024 else 1575
SCREENHEIGHT = args.height if args.height else 768 if args.res == 1024 else 875
PIPEGAPSIZE  = 300 # gap between upper and lower part of pipe
BASEY        = SCREENHEIGHT * 0.79
# image, sound and hitmask  dicts
IMAGES, SOUNDS, HITMASKS = {}, {}, {}
SCREEN, FPSCLOCK = '', ''
HIGHSCORE = 0

# list of all possible players (tuple of 3 positions of flap)
PLAYERS_LIST = (
    # flying pig
    (
        'assets/sprites/flypig-upflap-HD.png',
        'assets/sprites/flypig-midflap-HD.png',
        'assets/sprites/flypig-downflap-HD.png',
    ),
    (
        'assets/sprites/flyingPig_upflap.png',
        'assets/sprites/flyingPig_midflap.png',
        'assets/sprites/flyingPig_downflap.png',
    ),
)

# list of backgrounds
BACKGROUNDS_LIST = (
    'assets/sprites/background-day-HD-repeatable.png',
    'assets/sprites/background-night-HD-repeatable.png',
)

# list of pipes
PIPES_LIST = (
    'assets/sprites/florenceYall-HD.png',
    'assets/sprites/pipe-green-rosemary-HD.png',
    'assets/sprites/pipe-red-JamesBrown-HD.png',
)

clapped = pygame.event.Event(pygame.USEREVENT, attr1='clapped')
clapReadyEvent = pygame.USEREVENT + 1
welcomeReadyEvent = pygame.USEREVENT + 1


try:
    xrange
except NameError:
    xrange = range

def main():
    global SCREEN, FPSCLOCK
    pygame.init()
    FPSCLOCK = pygame.time.Clock()
    SCREEN = pygame.display.set_mode((SCREENWIDTH, SCREENHEIGHT)) #, pygame.NOFRAME
    pygame.display.set_caption('Clappy Pig')
    #pygame.time.set_timer(clapReadyEvent, 200) # Reset clapReady on game startup

    # numbers sprites for score display
    IMAGES['numbers'] = (
        pygame.image.load('assets/sprites/0.png').convert_alpha(),
        pygame.image.load('assets/sprites/1.png').convert_alpha(),
        pygame.image.load('assets/sprites/2.png').convert_alpha(),
        pygame.image.load('assets/sprites/3.png').convert_alpha(),
        pygame.image.load('assets/sprites/4.png').convert_alpha(),
        pygame.image.load('assets/sprites/5.png').convert_alpha(),
        pygame.image.load('assets/sprites/6.png').convert_alpha(),
        pygame.image.load('assets/sprites/7.png').convert_alpha(),
        pygame.image.load('assets/sprites/8.png').convert_alpha(),
        pygame.image.load('assets/sprites/9.png').convert_alpha()
    )

    # game over sprite
    IMAGES['art'] = pygame.image.load('assets/sprites/Proscenium-damask-material.png').convert_alpha()
    # game over sprite
    IMAGES['gameover'] = pygame.image.load('assets/sprites/gameoverNew.png').convert_alpha()
    # message sprite for welcome screen
    IMAGES['message'] = pygame.image.load('assets/sprites/messageNew.png').convert_alpha()
    IMAGES['badge'] = pygame.image.load('assets/sprites/corner-badge.png').convert_alpha()
    # base (ground) sprite
    IMAGES['base'] = pygame.image.load('assets/sprites/baseNew.png').convert_alpha()
    # highscore text sprite
    IMAGES['highscore'] = pygame.image.load('assets/sprites/highscore4.png').convert_alpha()
    IMAGES['highscore_new'] = pygame.image.load('assets/sprites/highscoreNew.png').convert_alpha()

    # sounds
    if 'win' in sys.platform:
        soundExt = '.wav'
    else:
        soundExt = '.ogg'

    SOUNDS['die']    = pygame.mixer.Sound('assets/audio/die' + soundExt)
    SOUNDS['hit']    = pygame.mixer.Sound('assets/audio/hit' + soundExt)
    SOUNDS['point']  = pygame.mixer.Sound('assets/audio/point' + soundExt)
    SOUNDS['swoosh'] = pygame.mixer.Sound('assets/audio/swoosh' + soundExt)
    SOUNDS['wing']   = pygame.mixer.Sound('assets/audio/wing' + soundExt)

    while True:
        # select random background sprites
        randBg = random.randint(0, len(BACKGROUNDS_LIST) - 1)
        IMAGES['background'] = pygame.image.load(BACKGROUNDS_LIST[randBg]).convert()

        # select random player sprites
        randPlayer = random.randint(0, len(PLAYERS_LIST) - 1)
        IMAGES['player'] = (
            pygame.image.load(PLAYERS_LIST[randPlayer][0]).convert_alpha(),
            pygame.image.load(PLAYERS_LIST[randPlayer][1]).convert_alpha(),
            pygame.image.load(PLAYERS_LIST[randPlayer][2]).convert_alpha(),
        )

        # select random pipe sprites
        pipeindex = random.randint(0, len(PIPES_LIST) - 1)
        IMAGES['pipe'] = (
            pygame.transform.flip(
                pygame.image.load(PIPES_LIST[pipeindex]).convert_alpha(), False, True),
            pygame.image.load(PIPES_LIST[pipeindex]).convert_alpha(),
        )

        # hismask for pipes
        HITMASKS['pipe'] = (
            getHitmask(IMAGES['pipe'][0]),
            getHitmask(IMAGES['pipe'][1]),
        )

        # hitmask for player
        HITMASKS['player'] = (
            getHitmask(IMAGES['player'][0]),
            getHitmask(IMAGES['player'][1]),
            getHitmask(IMAGES['player'][2]),
        )

        movementInfo = showWelcomeAnimation()
        crashInfo = mainGame(movementInfo)
        showGameOverScreen(crashInfo)


def showWelcomeAnimation(isClapReady = False):
    global backgrounds
    """Shows welcome screen animation of flappy bird"""
    # index of player to blit on screen
    if not isClapReady:
        pygame.time.set_timer(welcomeReadyEvent, 800)
    
    playerIndex = 0
    playerIndexGen = cycle([0, 1, 2, 1])
    # iterator used to change playerIndex after every 5th iteration
    loopIter = 0

    backgrounds = [
        {'x': 0, 'y': 0},
        {'x': IMAGES['background'].get_width(), 'y': 0}
    ]

    playerx = int(SCREENWIDTH * 0.2)
    playery = int((SCREENHEIGHT - IMAGES['player'][0].get_height()) / 2)

    messagex = int((SCREENWIDTH - IMAGES['message'].get_width()) / 2)
    messagey = int(SCREENHEIGHT * 0.2)

    basex = 0
    backx = 0
    # amount by which base can maximum shift to left
    baseShift = IMAGES['base'].get_width() - IMAGES['background'].get_width()

    # player shm for up-down motion on welcome screen
    playerShmVals = {'val': 0, 'dir': 1}

    while True:
        for event in pygame.event.get():
            if event.type == pygame.locals.QUIT or (event.type == pygame.locals.KEYDOWN and event.key == pygame.locals.K_ESCAPE):
                pygame.quit()
                sys.exit()
            if event == clapped and isClapReady:
                # make first flap sound and return values for mainGame
                SOUNDS['wing'].play()
                return {
                    'playery': playery + playerShmVals['val'],
                    'basex': basex,
                    'playerIndexGen': playerIndexGen,
                }
            if event.type == welcomeReadyEvent:
                isClapReady = True

        # adjust playery, playerIndex, basex
        if (loopIter + 1) % 5 == 0:
            playerIndex = next(playerIndexGen)
        loopIter = (loopIter + 1) % 30
        basex = -((-basex + 4) % baseShift)
        playerShm(playerShmVals)

        # draw sprites
        for background in backgrounds:
            background['x'] -= 1
            SCREEN.blit(IMAGES['background'], (background['x'], background['y']))

        SCREEN.blit(IMAGES['player'][playerIndex],
                    (playerx, playery + playerShmVals['val']))
        showHighscore(HIGHSCORE)
        SCREEN.blit(IMAGES['message'], (messagex, messagey))
        SCREEN.blit(IMAGES['base'], (basex, BASEY))

        # remove background if its off the screen
        if backgrounds[0]['x'] < -IMAGES['background'].get_width():
            backgrounds.pop(0)
            backgrounds.append(getBackground())

        pygame.display.update()
        FPSCLOCK.tick(FPS)

def mainGame(movementInfo):
    BASESPEED = 3.0 # the speed pipes and base move
    clapReady = True
    score = playerIndex = loopIter = 0
    playerIndexGen = movementInfo['playerIndexGen']
    playerx, playery = int(SCREENWIDTH * 0.2), movementInfo['playery']

    basex = movementInfo['basex']
    baseShift = IMAGES['base'].get_width() - IMAGES['background'].get_width()

    # get 2 new pipes to add to upperPipes lowerPipes list
    newPipe1 = getRandomPipe()
    newPipe2 = getRandomPipe()
    # list of upper pipes
    upperPipes = [
        {'x': SCREENWIDTH + 200, 'y': newPipe1[0]['y'], 'moving': False, 'move_direc': 'up'},
        {'x': SCREENWIDTH + 200 + (SCREENWIDTH / 2), 'y': newPipe2[0]['y'], 'moving': False, 'move_direc': 'down'},
    ]

    # list of lowerpipe
    lowerPipes = [
        {'x': SCREENWIDTH + 200, 'y': newPipe1[1]['y'], 'moving': False, 'move_direc': 'up'},
        {'x': SCREENWIDTH + 200 + (SCREENWIDTH / 2), 'y': newPipe2[1]['y'], 'moving': False, 'move_direc': 'down'},
    ]

    pipeVelX = -4

    # player velocity, max velocity, downward accleration, accleration on flap
    playerVelY    =  -13   # player's velocity along Y, default same as playerFlapped
    playerMaxVelY =  10   # max vel along Y, max descend speed
    # playerMinVelY =  -8   # min vel along Y, max ascend speed - UNUSED
    playerAccY    =   1   # players downward accleration
    playerRot     =  45   # player's rotation
    playerVelRot  =   3   # angular speed
    playerRotThr  =  20   # rotation threshold
    playerFlapAcc =  -13   # players speed on flapping
    playerFlapped = False # True when player flaps

    while True:
        for event in pygame.event.get():
            if event.type == pygame.locals.QUIT or (event.type == pygame.locals.KEYDOWN and event.key == pygame.locals.K_ESCAPE):
                pygame.quit()
                sys.exit()
            if event == clapped and clapReady == True:
                if playery > -2 * IMAGES['player'][0].get_height():
                    playerVelY = playerFlapAcc
                    playerFlapped = True
                    SOUNDS['wing'].play()
                    clapReady = False
                    pygame.time.set_timer(clapReadyEvent, 200)
            if event.type == clapReadyEvent:
                clapReady = True

        # check for crash here
        crashTest = checkCrash({'x': playerx, 'y': playery, 'index': playerIndex},
                               upperPipes, lowerPipes)
        if crashTest[0]:
            return {
                'y': playery,
                'groundCrash': crashTest[1],
                'basex': basex,
                'upperPipes': upperPipes,
                'lowerPipes': lowerPipes,
                'score': score,
                'playerVelY': playerVelY,
                'playerRot': playerRot
            }

        # check for score
        playerMidPos = playerx + IMAGES['player'][0].get_width() / 2
        for pipe in upperPipes:
            pipeMidPos = pipe['x'] + IMAGES['pipe'][0].get_width() / 2
            if pipeMidPos <= playerMidPos < pipeMidPos + (BASESPEED * 4):
                score += 1
                SOUNDS['point'].play()

                # Increase speed every 5 successful jumps:
                if score >= 10 and score % 5 == 0:
                    BASESPEED += 0.5

        # playerIndex basex change
        if (loopIter + 1) % 3 == 0:
            playerIndex = next(playerIndexGen)
        loopIter = (loopIter + 1) % 30
        basex = -((-basex + (BASESPEED * 100)) % baseShift)

        # rotate the player
        if playerRot > -90:
            playerRot -= playerVelRot

        # player's movement
        if playerVelY < playerMaxVelY and not playerFlapped:
            playerVelY += playerAccY
        if playerFlapped:
            playerFlapped = False

            # more rotation to cover the threshold (calculated in visible rotation)
            playerRot = 45

        playerHeight = IMAGES['player'][playerIndex].get_height()
        playery += min(playerVelY, BASEY - playery - playerHeight)

        # move pipes to left
        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            uPipe['x'] += BASESPEED * pipeVelX
            lPipe['x'] += BASESPEED * pipeVelX

        # draw background, move it to left each frame
        for background in backgrounds:
            background['x'] -= 1
            SCREEN.blit(IMAGES['background'], (background['x'], background['y']))

        # remove background if its off the screen
        if backgrounds[0]['x'] < -IMAGES['background'].get_width():
            backgrounds.pop(0)
            backgrounds.append(getBackground())

        # add new pipe when first pipe is about to touch left of screen
        if upperPipes[0]['x'] < 100 and len(upperPipes) <= 2:
            if score >= 5:
                newPipe = getRandomPipe(True) # passing True makes pipes move up and down
            else:
                newPipe = getRandomPipe()
            upperPipes.append(newPipe[0])
            lowerPipes.append(newPipe[1])

        # remove first pipe if its out of the screen
        if upperPipes[0]['x'] < -IMAGES['pipe'][0].get_width():
            upperPipes.pop(0)
            lowerPipes.pop(0)

        # draw sprites
        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            SCREEN.blit(pygame.transform.flip(IMAGES['pipe'][0], True, False), (uPipe['x'], uPipe['y']))
            SCREEN.blit(IMAGES['pipe'][1], (lPipe['x'], lPipe['y']))

            if(uPipe['moving']):
                if uPipe['move_direc'] == 'down':
                    uPipe['y'] += 2
                    lPipe['y'] += 2
                    if uPipe['y'] >= -300:
                        uPipe['move_direc'] = 'up'
                elif uPipe['move_direc'] == 'up':
                    uPipe['y'] -= 2
                    lPipe['y'] -= 2
                    if uPipe['y'] <= -500:
                        uPipe['move_direc'] = 'down'

        SCREEN.blit(IMAGES['base'], (basex, BASEY))
        # print score so player overlaps the score
        showScore(score)

        # Player rotation has a threshold
        visibleRot = playerRotThr
        if playerRot <= playerRotThr:
            visibleRot = playerRot
        
        playerSurface = pygame.transform.rotate(IMAGES['player'][playerIndex], visibleRot)
        SCREEN.blit(playerSurface, (playerx, playery))

        pygame.display.update()
        FPSCLOCK.tick(FPS)

def showGameOverScreen(crashInfo, isClapReady = False):
    """crashes the player down ans shows gameover image"""
    global HIGHSCORE
    clapReady = isClapReady
    score = crashInfo['score']
    playerx = SCREENWIDTH * 0.2
    playery = crashInfo['y']
    playerHeight = IMAGES['player'][0].get_height()
    playerVelY = crashInfo['playerVelY']
    playerAccY = 2
    playerRot = crashInfo['playerRot']
    playerVelRot = 7
    isNew = False
    start_ticks=pygame.time.get_ticks()

    basex = crashInfo['basex']

    upperPipes, lowerPipes = crashInfo['upperPipes'], crashInfo['lowerPipes']

    # play hit and die sounds
    SOUNDS['hit'].play()
    if not crashInfo['groundCrash']:
        SOUNDS['die'].play()

    while True:
        seconds = (pygame.time.get_ticks() - start_ticks)/1000 # calculate how many seconds
        if(seconds > 5):
            return
        for event in pygame.event.get():
            if event.type == pygame.locals.QUIT or (event.type == pygame.locals.KEYDOWN and event.key == pygame.locals.K_ESCAPE):
                pygame.quit()
                sys.exit()
            if event == clapped and clapReady:
                if playery + playerHeight >= BASEY - 1:
                    return
            if event.type == clapReadyEvent:
                clapReady = True


        # player y shift
        if playery + playerHeight < BASEY - 1:
            playery += min(playerVelY, BASEY - playery - playerHeight)

        # player velocity change
        if playerVelY < 15:
            playerVelY += playerAccY

        # rotate only when it's a pipe crash
        if not crashInfo['groundCrash']:
            if playerRot > -90:
                playerRot -= playerVelRot

        # draw sprites
        for background in backgrounds:
            SCREEN.blit(IMAGES['background'], (background['x'], background['y']))

        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            SCREEN.blit(pygame.transform.flip(IMAGES['pipe'][0], True, False), (uPipe['x'], uPipe['y']))
            SCREEN.blit(IMAGES['pipe'][1], (lPipe['x'], lPipe['y']))

        SCREEN.blit(IMAGES['base'], (basex, BASEY))
        showScore(score)

        playerSurface = pygame.transform.rotate(IMAGES['player'][1], playerRot)
        SCREEN.blit(playerSurface, (playerx,playery))
        SCREEN.blit(IMAGES['gameover'], (SCREENWIDTH/2 - (IMAGES['gameover'].get_width()/2), SCREENHEIGHT/2 - (IMAGES['gameover'].get_height()/2)))
        if(score > HIGHSCORE or isNew):
            HIGHSCORE = score
            showHighscore(HIGHSCORE, True)
            isNew = True
        else:
            showHighscore(HIGHSCORE, False)
        FPSCLOCK.tick(FPS)
        pygame.display.update()

def playerShm(playerShm):
    """oscillates the value of playerShm['val'] between 8 and -8"""
    if abs(playerShm['val']) == 16:
        playerShm['dir'] *= -1

    if playerShm['dir'] == 1:
        playerShm['val'] += 1
    else:
        playerShm['val'] -= 1

def getRandomPipe(moving = False):
    """returns a randomly generated pipe"""
    # y of gap between upper and lower pipe
    gapY = random.randrange(0, int(BASEY * 0.6 - PIPEGAPSIZE))
    gapY += int(BASEY * 0.2)
    pipeHeight = IMAGES['pipe'][0].get_height()
    pipeX = SCREENWIDTH + 10

    direction = ['up', 'down'][random.randrange(0,2)]
    oppo_direc = 'up' if direction == 'down' else 'down' # ternary conditional to get opposite direction
    
    return [
        {'x': pipeX, 'y': gapY - pipeHeight, 'moving': moving, 'move_direc': direction},  # upper pipe
        {'x': pipeX, 'y': gapY + PIPEGAPSIZE, 'moving': moving, 'move_direc': oppo_direc}, # lower pipe
    ]

def showScore(score):
    """displays score in center of screen"""
    scoreDigits = [int(x) for x in list(str(score))]
    totalWidth = 0 # total width of all numbers to be printed

    for digit in scoreDigits:
        totalWidth += IMAGES['numbers'][digit].get_width()

    Xoffset = (SCREENWIDTH - totalWidth) / 2

    for digit in scoreDigits:
        SCREEN.blit(IMAGES['numbers'][digit], (Xoffset, SCREENHEIGHT * 0.1))
        Xoffset += IMAGES['numbers'][digit].get_width()

def showHighscore(score, isNew = False):
    global HIGHSCORE
    
    scoreDigits = [int(x) for x in list(str(HIGHSCORE))]
    totalWidth = 0 # total width of all numbers to be printed

    for digit in scoreDigits:
        totalWidth += IMAGES['numbers'][digit].get_width()

    Xoffset = (SCREENWIDTH*0.02) + IMAGES['highscore'].get_width()

    # highscore background corner
    SCREEN.blit(IMAGES['badge'], (-130 + totalWidth, SCREENHEIGHT * -0.03 if not isNew else 0))

    for digit in scoreDigits:
        if(isNew):
            SCREEN.blit(IMAGES['numbers'][digit], (Xoffset, SCREENHEIGHT * 0.04))
            Xoffset += IMAGES['numbers'][digit].get_width()
        else:
            SCREEN.blit(IMAGES['numbers'][digit], (Xoffset, SCREENHEIGHT * 0.01))
            Xoffset += IMAGES['numbers'][digit].get_width()
    
    if(isNew):
        SCREEN.blit(IMAGES['highscore_new'], (SCREENWIDTH * 0.01, SCREENHEIGHT * 0.01))
    else:
        SCREEN.blit(IMAGES['highscore'], (SCREENWIDTH * 0.01, SCREENHEIGHT * 0.01))

def checkCrash(player, upperPipes, lowerPipes):
    """returns True if player collders with base or pipes."""
    pi = player['index']
    player['w'] = IMAGES['player'][0].get_width()
    player['h'] = IMAGES['player'][0].get_height()

    # if player crashes into ground
    if player['y'] + player['h'] >= BASEY - 1:
        return [True, True]
    else:

        playerRect = pygame.Rect(player['x'], player['y'],
                      player['w'], player['h'])
        pipeW = IMAGES['pipe'][0].get_width()
        pipeH = IMAGES['pipe'][0].get_height()

        for uPipe, lPipe in zip(upperPipes, lowerPipes):
            # upper and lower pipe rects
            uPipeRect = pygame.Rect(uPipe['x'], uPipe['y'], pipeW, pipeH)
            lPipeRect = pygame.Rect(lPipe['x'], lPipe['y'], pipeW, pipeH)

            # player and upper/lower pipe hitmasks
            pHitMask = HITMASKS['player'][pi]
            uHitmask = HITMASKS['pipe'][0]
            lHitmask = HITMASKS['pipe'][1]

            # if bird collided with upipe or lpipe
            uCollide = pixelCollision(playerRect, uPipeRect, pHitMask, uHitmask)
            lCollide = pixelCollision(playerRect, lPipeRect, pHitMask, lHitmask)

            if uCollide or lCollide:
                return [True, False]

    return [False, False]

def pixelCollision(rect1, rect2, hitmask1, hitmask2):
    """Checks if two objects collide and not just their rects"""
    rect = rect1.clip(rect2)

    if rect.width == 0 or rect.height == 0:
        return False

    x1, y1 = rect.x - rect1.x, rect.y - rect1.y
    x2, y2 = rect.x - rect2.x, rect.y - rect2.y

    for x in xrange(rect.width):
        for y in xrange(rect.height):
            if hitmask1[x1+x][y1+y] and hitmask2[x2+x][y2+y]:
                return True
    return False

def getHitmask(image):
    """returns a hitmask using an image's alpha."""
    mask = []
    for x in xrange(image.get_width()):
        mask.append([])
        for y in xrange(image.get_height()):
            mask[x].append(bool(image.get_at((x,y))[3]))
    return mask

def getBackground():
    return {'x': IMAGES['background'].get_width(), 'y': 0}

if __name__ == '__main__':
    main()
