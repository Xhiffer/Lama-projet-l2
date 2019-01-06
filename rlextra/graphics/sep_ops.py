#copyright ReportLab Europe Limited. 2000-2016
SEP_OPS='''
%%BeginResource: procset sep_ops 1.03 0
%%Title: (Separation Procs)
%%Version: 1.03 0
userdict /sep_ops 50 dict dup begin put
/bdef {bind def} bind def
/xdef {exch def} bdef
/colorimagebuffer { % helper proc called by customcolorimage
	0 1 2 index length 1 sub {
	dup 2 index exch get 255 exch sub 2 index 3 1 roll put
	}for
}bdef

/addprocs { % {proc1} {proc2} addprocs {{proc1}exec {proc2} exec}
	[ 3 1 roll
	/exec load
	dup 3 1 roll
	] cvx
} bdef

/L1? {
	/languagelevel where {
	pop languagelevel 2 lt
	}{
		true
	} ifelse
} bdef

/colorexists { % tests to see if printing on color device
	statusdict /processcolors known {
		statusdict /processcolors get exec
	}{ % processcolors not present
		/deviceinfo where { % check for dps environment
			pop deviceinfo /Colors known {
				deviceinfo /Colors get % get color value from DPS
				statusdict /processcolors {% add processcolors entry
					deviceinfo /Colors known {
						deviceinfo /Colors get
						}{
					1
				} ifelse
			} put
		}{
		1
	} ifelse
}{ % not in dps environment, assume monochrome
1
} ifelse
} ifelse
1 gt % return true for color devices, false for B&W
} bdef
/MakeReadOnlyArray { % size => [array]
/packedarray where {
pop packedarray
}{
array astore readonly
} ifelse
} bdef
/findcmykcustomcolor where {
pop
}{
/findcmykcustomcolor {% c m y k name findcmykcustomcolor array
5 MakeReadOnlyArray
} bdef
} ifelse
/setoverprint where {
pop
}{
/setoverprint {% boolean setoverprint -
pop
} bdef
} ifelse
/setcustomcolor where {
pop
}{
L1? {
/setcustomcolor { % array tint setcustomcolor -
exch
aload pop pop
4 { 4 index mul 4 1 roll } repeat
5 -1 roll pop
setcmykcolor
} bdef
}{
/setcustomcolor { % customcolorarray tint
exch
[ exch /Separation exch dup 4 get exch /DeviceCMYK exch
0 4 getinterval
[ exch /dup load exch cvx {mul exch dup}
/forall load /pop load dup] cvx
] setcolorspace setcolor
} bdef
} ifelse
} ifelse
% initialize variables to avoid unintentional early binding
/ik 0 def /iy 0 def /im 0 def /ic 0 def
/imagetint {% converts cmyk to grayscale equiv w/red book formula
% called by setcmykcolor and customcolorimage procs.
ic .3 mul
im .59 mul
iy .11 mul
ik add add add dup
1 gt{pop 1}if
} bdef
/setcmykcolor where {
pop
}{
% setcmykcolor not supported, call setgray instead
/setcmykcolor { % c m y k setcmykcolor --
/ik xdef /iy xdef /im xdef /ic xdef
imagetint
1 exch sub setgray
} bdef
} ifelse
/customcolorimage where {
pop
}{
L1? {
/customcolorimage{ % w h bps matrix proc array
gsave
colorexists {
aload pop pop
/ik xdef /iy xdef /im xdef /ic xdef
currentcolortransfer
{ik mul ik sub 1 add} addprocs
4 1 roll {iy mul iy sub 1 add} addprocs
4 1 roll{im mul im sub 1 add} addprocs
4 1 roll{ic mul ic sub 1 add} addprocs
4 1 roll setcolortransfer
/magentabuf 0 string def
/yellowbuf 0 string def
/blackbuf 0 string def
{
colorimagebuffer dup length magentabuf length ne{
dup length dup dup
/magentabuf exch string def
/yellowbuf exch string def
/blackbuf exch string def
}if
dup magentabuf copy yellowbuf copy
blackbuf copy pop
} addprocs
{magentabuf}{yellowbuf}{blackbuf} true 4 colorimage
}{ % non-color device
aload pop pop /ik xdef /iy xdef /im xdef /ic xdef
/tint imagetint def
currenttransfer
{tint mul 1 tint sub add} addprocs settransfer image
}ifelse
grestore
} bdef
}{ % Level 2 environment
/customcolorimage { % w h bps matrix proc array
gsave
[ exch /Separation exch dup 4 get exch /DeviceCMYK exch
0 4 getinterval
[ exch /dup load exch cvx {mul exch dup}
/forall load /pop load dup] cvx
] setcolorspace
10 dict begin
/ImageType 1 def
/DataSource exch def
/ImageMatrix exch def
/BitsPerComponent exch def
/Height exch def
/Width exch def
/Decode [1 0] def
currentdict end
image
grestore
} bdef
} ifelse
} ifelse
/setseparationgray where {
pop
}{
L1? {
/setseparationgray {
1 exch sub dup dup dup setcmykcolor
} bdef
}{
/setseparationgray {
[/Separation /All /DeviceCMYK
{dup dup dup}] setcolorspace 1 exch sub setcolor
} bdef
} ifelse
} ifelse
/separationimage where {
pop
}{
/separationimage {
gsave
1 1 1 1 (All)
findcmykcustomcolor customcolorimage
grestore
} bdef
} ifelse
currentdict readonly pop end
%%EndResource
'''
