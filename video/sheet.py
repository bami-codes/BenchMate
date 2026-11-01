import sys
from PIL import Image
files=sys.argv[2:]; out=sys.argv[1]
W,H=960,540; rows=(len(files)+1)//2; sheet=Image.new('RGB',(W*2,H*rows),'white')
for i,f in enumerate(files): sheet.paste(Image.open(f).resize((W,H)),((i%2)*W,(i//2)*H))
sheet.save(out,quality=88)
