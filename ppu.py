from itertools import cycle


class PPU:
	def __init__(self):
		# 256 x 256 grid but displays 160 x 144 (32x32 -> 20x18 to tiles)
		self.vram = [0] * 0x2000 # 0x8000 - 0x9FFF, Backgorund and Window
		self.oam = [0] * 0xA0 # 0xFE00 - 0xFE9F, object attribute memory
		
		self.scanline_y = 0

		'''
		contains data used to display Sprites (also known as “Objects”) on screen. 
		Each sprite takes up 4 bytes in this section of memory, allowing for a total of 40 sprites 
		to be displayed at any given time
		'''

		'''
		oam sprite data (up to 40 sprites)
		
		Byte 0 - y position (16 is subtracted from this value to determine the actual Y-Position. 
		This means that a Y-Position of 16 would place the sprite at the top border of the screen.)
		
		Byte 1 - x position (moving sprites into frame smoothly is allowed by subtracting 8 from this value. 
		This means that an X-Position of 8 would place the sprite at the left border of the screen, whereas a 
		value of 0 would fully hide the sprite.)
		
		Byte 2 - tile number (used for fetching the graphics data for the sprite. Note that sprites always use 
		the “8000 addressing method”, so this value is always interpreted as an unsigned 8-bit integer.)
		
		Byte 3 - sprite flags (from 7 to 0: OBJ-to-BG Priority, Y-flip, X-flip, pallete number, CGB-flags)
		
		7 - set 0 if background, 1 if window
		4 - If set to 0, the OBP0 register is used as the palette, otherwise OBP
		0-3: color gameboy (don't worry about this yet)

		Basically, where it is, what number it is, and what color
		'''
		
		self.LY = 0 # row
		self.LX = 0 # col
		self.FStep = 0 #bool for what stage in fethcing we're on
		self.tLow = 0
		self.tHigh = 0

		self.LCDC = 0x0
		self.LCDStat = 0x0
		#background
		self.SCX = 0x0 #screen x - left to right
		self.SCY = 0x0 #screen y - top to bottom
		#window
		self.WX = 0x0 #0xFF4B, oam
		self.WY = 0x0 #0xFF4A, oam
		self.BGP = 0x0
		self.frame = [[0] * 144] * 160 #LCD

		self.m_cycles_passed = 0 # % 114
		#OAM 40
		#Draw +43
		#H-blank +31
		self.LYC = 0
		#LYC > 160 -> V-blank
		self.BGFIFO = []
		self.SprFIFO = []

		#TILE 8x8 pixels
		#TILE_NUMBER = unsigned byte
		#tile = TILE_NUMBER * 16 (8010 = tile 1)
		#signed variant does the same and uses 9000 as a base

	def sprite_fetcher(self):
		if self.FStep:
			TILE_MAP = 0x9800

			tile_x = (self.LX + (self.SCX / 8)) & 0x1F
			tile_y = 32 * (((self.LY + self.SCY) & 0xFF) / 8)

			TILE_NUMBER = self.vram[((TILE_MAP + ((tile_x + tile_y) & 0x3FF)) - 0x8000)] #from sprite buffer
			offset = 2 * ((self.LY + self.SCY) % 8)

			tile = 0x8000 + (TILE_NUMBER * 16)

			self.tLow = self.vram[((tile + offset) - 0x8000)]
			
			self.FStep = not self.FStep

		else:
			offset = 2 * ((self.LY + self.SCY) % 8)

			tile = 0x8000 + (TILE_NUMBER * 16)

			self.tHigh = self.vram[((tile + offset) - 0x8000)]

			if len(self.SprFIFO) <= 8:
				for i in range(8):
					self.SprFIFO[i] = ((((self.tHigh >> (7 - i)) & 0x1) << 1) | ((self.tLow >> (7 - i)) & 0x1)) 		
			self.fetcherX += 1
			
			self.FStep = not self.FStep

	def background_fetcher(self):
		if self.FStep: #steps 1 & 2
			TILE_MAP = 0x9800

			tile_x = (self.LX + (self.SCX / 8)) & 0x1F
			tile_y = 32 * (((self.LY + self.SCY) & 0xFF) / 8)

			TILE_NUMBER = self.vram[((TILE_MAP + ((tile_x + tile_y) & 0x3FF)) - 0x8000)]
			#32 * (WINDOW_LINE_COUNTER / 8)

			offset = 2 * ((self.LY + self.SCY) % 8)
			#2 * (WINDOW_LINE_COUNTER % 8)
			
			if((self.LCDC >> 4) & 1):
				tile = 0x8000 + (TILE_NUMBER * 16)
			else:
				tile = (0x9000 + (TILE_NUMBER * 16)) & 0xFFFF

			self.tLow = self.vram[((tile + offset) - 0x8000)]
			
			self.FStep = not self.FStep 

		else:
			offset = 2 * ((self.LY + self.SCY) % 8)

			if((self.LCDC >> 4) & 1):
				tile = 0x8000 + (TILE_NUMBER * 16)
			else:
				tile = (0x9000 + (TILE_NUMBER * 16)) & 0xFFFF


			self.tHigh = self.vram[((tile + offset) - 0x8000)]

			if len(self.BGFIFO) <= 8:
				for i in range(8):
					self.BGFIFO[i] = ((((self.tHigh >> (7 - i)) & 0x1) << 1) | ((self.tLow >> (7 - i)) & 0x1)) 		
			self.fetcherX += 1
			
			self.FStep = not self.FStep

	def HBLANK(self):
		pass

	def VBLANK(self):
		pass

	def OAMSCAN(self):
		pass

	def DRAW(self):
		'''
		if((self.LCDC >> 3) & (self.LCDC >> 5)):
			both?

		if((self.LCDC >> 3) & 1):
			self.background_fetcher()

		if((self.LCDC >> 5) & 1):
			self.window?_fetcher()
		'''
		#If the X-Position of any sprite in the sprite buffer is less than or equal to the 
		#current Pixel-X-Position + 8, a sprite fetch is initiated.

		self.background_fetcher()

		if len(self.BGFIFO) >= 8:

			if (self.tick_state.scanline_x == 0) and not self.rendered_window_on_scanline:
				for _ in range(self.SCX % 8):
					self.BGFIFO.pop(0);
			#at the start of each scanline discard SCX mod 8 pixels from FIFO and push the rest to LCD 
			#** A BIT INACCURATE EACH REMOVAL SHOULD BE A cycle
                               
			#send to LCD and clear BGFIFO
			#self.frame[self.LYC][self.scanline_y]
			#self.scanline_y += 1

			pass

		pass

	def tick(self):
		if self.LYC >= 160:
			self.VBLANK()
		else:
			scanline_cycles = self.m_cycles_passed % 114

			if scanline_cycles < 40:
				self.OAMSCAN()
			if scanline_cycles < 83:
				self.DRAW()
			else:
				self.HBLANK()

		# END OF SCANLINE RESET SCANLINE_Y TO 0


	'''
	a “scanline” is simply a row of pixels on the screen. The PPU goes from left to 
	right along the scanline and places the pixels one by one, and once it’s done, it continues 
	to the next scanline. Do note that the PPU operates on a pixel-basis, and not on a tile-basis.
	
	Each scan line takes 45d t-cycles
	456/4 = 114 m-cycles

	PPU modes: 2->3->0->2 (1 occurs at the end of every frame)
		0: H-blank - This mode takes up the remainder of the scanline after the Drawing Mode finishes, 
		more or less “padding” the duration of the scanline to a total of 456 T-Cycles. The PPU effectively 
		pauses during this mode.
		
		1: V-blank - the same as H-Blank in the way that the PPU does not draw any pixels to the LCD during its 
		duration. However, instead of it taking place at the end of every scanline, it’s a much longer period at the end of 
		every frame (execute at scanline 160)
		
		As the Gameboy has a vertical resolution of 144 pixels, it would be expected that the amount of scanlines the PPU 
		handles would be equal - 144 scanlines. However, this is not the case. In reality there are 154 scanlines, the 10 
		last of which being “pseudo-scanlines” during which no pixels are drawn as the PPU is in the V-Blank state during 
		their duration. A V-Blank scanline takes the same amount of time as any other scanline - 456 T-Cycles.

		2: OAM scan - This mode is entered at the start of every scanline (except for V-Blank) 
		before pixels are actually drawn to the screen. During this mode the PPU searches OAM memory 
		for sprites that should be rendered on the current scanline and stores them in a buffer. This procedure 
		takes a total amount of 80 T-Cycles, meaning that the PPU checks a new OAM entry every 2 T-Cycles.
		A sprite is only added to the buffer if all of the following conditions apply:
			Sprite X-Position must be greater than 0
			LY + 16 must be greater than or equal to Sprite Y-Position
			LY + 16 must be less than Sprite Y-Position + Sprite Height (8 in Normal Mode, 16 in Tall-Sprite-Mode)
			The amount of sprites already stored in the OAM Buffer must be less than 10
			(essentially, as long as the sprite has room, and is in the OAM buffer near the front of the line)

		SpriteFIFO + BackgroundFIFO -> display (LCD)
		wait 40 cycles
		
		3: Drawing - The Drawing Mode is where the PPU transfers pixels to the LCD. The duration of this mode 
		changes depending on multiple variables, such as background scrolling, the amount of sprites on the scanline, 
		whether or not the window should be rendered, etc. All of the specifics to these timing differences will be 
		explained later on.


	

	https://hacktix.github.io/GBEDG/ppu/
	'''