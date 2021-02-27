import io
from typing import Hashable, Iterable, List, Tuple
import discord
import numpy as np
from PIL import Image
from random import randint
from wordcloud import WordCloud
from emoji_loader import server_emojis, uni_emojis
# proportions of the resulting image
width = 400
height = 200
scaling = 2


def is_overlapping(boxlist: List[Tuple[int, int, int, int]], x: int, y: int, size: int):
	for (emo_id, ox, oy, osize) in boxlist:
		if not (ox+osize < x or ox > x+size or oy > y+size or oy+osize < y):
			return True
	return len(boxlist) > 0


def make_boxlist(emolist: List[Tuple[Hashable, float]]) -> List[Tuple[Hashable, int, int, int]]:
	total = 0.0
	for (emoji, value) in emolist:
		total += value
	# compute random non-overalapping boxes for the custom emojis
	# boxlist is (emoji_id, x, y, size)
	boxlist: List[Tuple[int, int, int, int]] = []
	for (emoji, value) in emolist:
		# compute the size based on the relative strength of the emoji
		size = min(round(height / 2), round(height * value / total))
		# we only take the emoji if its worth a pixel in our image
		if size >= 4:
			size = max(16, size)
			# tries to generate a random non-overlapping box with this size (10 tries max)
			for tries in range(10):
				x = randint(0, width - size)
				y = randint(0, height - size)
				if not is_overlapping(boxlist, x, y, size):
					boxlist.append((emoji, x, y, size))
					break
			else:
				# we couldn't generate a non-overlapping box in 10 tries, we generate one without checking
				x = randint(0, width - size)
				y = randint(0, height - size)
				boxlist.append((emoji, x, y, size))
	return boxlist


def wc_image(server: discord.Guild, wc: Iterable[Tuple[str, float]]) -> io.BytesIO:
	"""
	make and save an word cloud image generated with words and emojis
	:param server: the server
	:param wc: the word cloud data
	:return: a virtual image file
	"""
	# compute emoji mapping
	emo_imgs = await server_emojis(server) | uni_emojis()
	# split the wc into words and emojis
	str_wc = []
	emo_wc = []
	for token, value in wc:
		if token in emo_imgs:
			emo_wc.append((token, value))
		else:
			str_wc.append((token, value))
	# we create the mask image
	mask = np.zeros(shape=(height, width), dtype=int)

	# compute the boxlist representing the space taken by emoji pics
	boxlist = make_boxlist(emo_wc)
	# apply every box in boxlist to the mask
	for (emo_id, x, y, size) in boxlist:
		mask[y:y + size, x:x + size] = 255

	# generate the image
	imgobject: Image = WordCloud(
		"Image/Fonts/OpenSansEmoji.otf", scale=scaling, max_words=None, mask=mask,
		background_color=None, mode="RGBA"
	).fit_words(dict(str_wc[:200])).to_image()

	# paste the emojis from boxlist to the image
	for (emo_id, x, y, size) in boxlist:
		# get the scaled emoji picture
		emo_img: Image = emo_imgs[emo_id].resize((size*scaling, size*scaling))
		# paste it in the pre-defined box
		imgobject.paste(emo_img, (x*scaling, y*scaling))

	# get and return the image bytes
	imgbytes = io.BytesIO()
	imgobject.save(imgbytes, format='PNG')
	imgbytes.seek(0)
	return imgbytes
