def genPassword(minpairs, maxpairs,hackspell=0):
    """
    Generate pronounceable passwords, modified from: 
        http://www.zopelabs.com/cookbook/1059673251
    """
    import random

    if hackspell:
        vowels='4a3e1io0u'
        consonants='8bcdfg9hjklmnpqrs5t7vwxyz2'
    else:
        vowels='aeiou'
        consonants='bcdfghjkl1mnpqrst4vwxyz'
    password=''

    for x in range(1,random.randint(int(minpairs),int(maxpairs))+1):
         consonant = consonants[random.randint(1,len(consonants)-1)]
         password=password + consonant
         vowel = vowels[random.randint(1,len(vowels)-1)]
         password=password + vowel

    return password

if __name__=='__main__':
    from optparse import OptionParser

    parser = OptionParser("%prog [options]")
    parser.add_option("-n", "--minimum",
                      type="int",
                      dest="minimum",
                      default=3,
                      help="minimum password syllables(%default)")
    parser.add_option("-x", "--maximum",
                      type="int",
                      dest="maximum",
                      default=5,
                      help="maximum password syllables(%default)")
    parser.add_option("-H", "--hackspell",
                      type="int",
                      dest="hackspell",
                      default=0,
                      help="use hacker spelling length(%default)")

    opts, args = parser.parse_args()
    print(genPassword(opts.minimum,opts.maximum,opts.hackspell))
