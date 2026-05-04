import math



bitdepth = 8 #16 # 8
lengthpow2 = 8

length = pow(2,lengthpow2)
columns = 16
scale = pow(2,bitdepth-lengthpow2)

gam_ = 2.6

def printblock():
  for ri in range(0,length,columns):
    for ci in range(columns):
      print(f"\t{(ri+ci)*scale},", end="")
    print('')


# B = L^(1/gam)
def lumtobrt(lum, gam=2.0, scale=255): 
  return pow(lum/scale, 1/gam)

def brttolum(brt, gam=2.0, scale=255): 
  return pow(brt/scale, gam)

def rangecorrect(n, min_=1):
  return min(n+(min_*scale), pow(2,bitdepth)-1)

print("flat:")
printblock()

print(f"lumtobrt gam {gam_}:")
for ri in range(0,length,columns):
  for ci in range(columns):
    print(f"\t{rangecorrect(int(pow(2,bitdepth)*lumtobrt(ri+ci,gam=gam_,scale=(length-1))))},", end="")
  print('')

print(f"brttolum gam {gam_}:")
for ri in range(0,length,columns):
  for ci in range(columns):
    print(f"\t{rangecorrect(int(pow(2,bitdepth)*brttolum(ri+ci,gam=gam_,scale=(length-1))))},", end="")
  print('')


