#copyright ReportLab Europe Limited. 2000-2016
#see license.txt for license details
"""Various sorting conveniences, for when the objects don't
have a natural order but they have some attributes which can
be used to sort them.  Nothing clever."""

def sortExplicit(stuff, preferredOrder):
    """Ensures any items in stuff appear in the
    same order they do in preferredOrder, and any which
    are not in preferredOrder appear at the end.
    
    """

    priorityMap = {}
    for i in range(len(preferredOrder)):
        thing = preferredOrder[i]
        priorityMap[thing] = i

    # all things not mentioned get a lower priority
    # than anything which is mentioned
    lowestPrio = i + 1
    sorter = []
    for thing in stuff:
        priority = priorityMap.get(thing, lowestPrio)
        sorter.append([priority, thing])
    sorter.sort()
    return [x[1] for x in sorter]
    

def sortOnColumn(stuff, columnIdx):
    sorter = []
    for row in stuff:
        priority = row[columnIdx]
        sorter.append([priority, row])
    sorter.sort()
    return [x[1] for x in sorter]
    
def sortOnAttribute(stuff, attr):
    sorter = []
    for thing in stuff:
        priority = getattr(thing, attr)
        sorter.append([priority, thing])
    sorter.sort()
    return [x[1] for x in sorter]
