# RPG Dice Roller
# by Ian Renton
# This code is licenced under the Creative Commons.
# See http://www.marmablue.co.uk/?q=node/2094 for details.
# version 0.3-20080522
# A dice-roller application with support for a number of RPG systems.

# TODO
# Crit Range (e.g. d20 crits on 19+, 18+ etc.)
# Shadowrun 4th Ed fail criteria

import wx
import random
import re

# Define a Roleplaying game system.  The meanings of each input parameter are as
# follows:
#   NAME: A unique name for the system.
#   FAMILY: The family of the system, e.g. "Storyteller".  For categorisation
#           only.
#   TYPE: "Overall Target" (D&D-esque), "Success-based" (Storyteller-esque),
#         "Roll & Keep" (7th Sea-esque), or "Free Entry".
#   FIXED QUANTITY: Make the user roll this many dice.  -1 = no restriction.
#   FIXED POLY: Make the user roll dice of this many sides.  -1 = no
#               restriction.
#   FIXED KEEP: Make the user keep only this many dice in a Roll & Keep.  -1 = 
#               no restriction.
#   FIXED TN: Fix the target number.  This is per die in "Success-based" and for
#             the total otherwise.  -1 = no restriction.
#   ROLL OVER/UNDER: Determines whether rolling over or under the TN is a
#                    success (per die, or overall).  "Over" and "Under" are
#                    obvious, "NoTN" means don't worry about success or failure,
#                    we just want the sum of the dice.  (This keeps d20 damage
#                    rolls in the "Overall Target" family.)  In the "Roll &
#                    Keep" family, it is assumed you keep the highest dice if
#                    this is "Over", and the lowest if this is "Under".
#   MIN IS BOTCH: Getting a 1 marks that die as a botch.  This also covers
#                 Natural 1s in d20.  Ignored in "Roll & Keep".  In
#                 "Success-based", the whole roll is only a botch if there are
#                 individual botches and there are no individual successes.
#   MIN IS -1 SUCCESS: Any 1s rolled subtract one from your number of successes.
#                      Only used in "Success-based".  Enable both this and the
#                      previous parameter (MIN IS BOTCH) to use the WoD 1st /
#                      2nd Ed behaviour whereby you can botch if you have more
#                      individual botches than individual successes (as opposed
#                      to the traditional behaviour whereby so long as you have
#                      at least one success, you're safe).
#   MAX EXPLODES: Any dice that get the maximum roll are rolled again, and the
#                 values added (Overall Target, Roll & Keep) or the successes
#                 added (Success-based).
#   MAX IS DOUBLE: Any dice that get the maximum roll count for two successes.
#                  Only used in "Success-based".
#   MAX IS SUCCESS: Any dice that get the maximum roll are successes, regardless
#                   of whether the TN was actually achievable or not.  This is
#                   only really for Natural 20s in d20.  Not in "Roll & Keep".
#   ALLOW ADDITION: Give the user the ability to add or subtract from the end of
#                   the roll, e.g. for 2d6+1.  "Overall Target" only.
class System:
    # Constructor
    def __init__(self,name,family,type,fixQuantity,fixPoly,fixKeep,fixTN,\
    rollOverUnder,minIsBotch,minIsMinusSuccess,maxExplodes,maxIsDouble,\
    maxIsSuccess,allowAddition):
        self.name = name
        self.family = family
        self.type = type
        self.fixQuantity = fixQuantity
        self.fixPoly = fixPoly
        self.fixKeep = fixKeep
        self.fixTN = fixTN
        self.rollOverUnder = rollOverUnder
        self.minIsBotch = minIsBotch
        self.minIsMinusSuccess = minIsMinusSuccess
        self.maxExplodes = maxExplodes
        self.maxIsDouble = maxIsDouble
        self.maxIsSuccess = maxIsSuccess
        self.allowAddition = allowAddition
    
    # When converted to a string, the System will report its name.
    def __str__(self):
        return "%s" % self.name
  
    
# Define the main frame of the GUI.
class MainFrame(wx.Frame):
    def __init__(self, parent, id, title):
        # First init a standard wxWidgets Frame.
        wx.Frame.__init__(self, parent, id, title)
        
        # Add the Family and System boxes
        panel = wx.Panel(self, -1)
        familyLabel = wx.StaticText(panel, -1, "Family:")
        systemLabel = wx.StaticText(panel, -1, "System:")
        self.family = wx.Choice(panel, -1, size=(150,-1))
        self.family.AppendItems(families.keys())
        self.family.Bind(wx.EVT_CHOICE,self.familyChanged)
        self.system = wx.Choice(panel, -1, size=(320,-1))
        self.system.Bind(wx.EVT_CHOICE,self.systemChanged)
        self.system.Enable(False)
        
        # Add the quantity, keep quantity, poly sides, addition and target 
        # number boxes
        quantityLabel = wx.StaticText(panel, -1, "Roll:")
        keepLabel = wx.StaticText(panel, -1, "Keep:")
        d = wx.StaticText(panel, -1, "d")
        plus = wx.StaticText(panel, -1, "+")
        targetLabel = wx.StaticText(panel, -1, "Target Number:")
        self.quantity = wx.TextCtrl(panel, -1, "", size=(40,-1))
        self.keep = wx.TextCtrl(panel, -1, "", size=(40,-1))
        self.poly = wx.TextCtrl(panel, -1, "", size=(40,-1))
        self.addition = wx.TextCtrl(panel, -1, "", size=(40,-1))
        self.target = wx.TextCtrl(panel, -1, "", size=(40,-1))
        self.quantity.Enable(False)
        self.keep.Enable(False)
        self.poly.Enable(False)
        self.addition.Enable(False)
        self.target.Enable(False)
        
        # Add the free entry area
        freeEntryLabel = wx.StaticText(panel, -1, "Free Entry:")
        self.freeEntry = wx.TextCtrl(panel, -1, "", size=(300,-1))
        self.freeEntry.Enable(False)
        
        # Add the roll button
        self.rollButton = wx.Button(panel, -1, "Roll!", size=(80,-1))
        self.rollButton.Bind(wx.EVT_BUTTON,self.rollDice)
        
        # Add output display
        self.display = wx.TextCtrl(panel, -1, "", size=(600,100),\
        style=wx.TE_MULTILINE|wx.TE_RICH)
        
        self.panel = panel

        # Arrange everything on the GUI
        topSizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        topSizer.Add(familyLabel, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 0)
        topSizer.Add(self.family, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        topSizer.Add(systemLabel, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 40)
        topSizer.Add(self.system, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        
        entrySizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        entrySizer.Add(quantityLabel, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 0)
        entrySizer.Add(self.quantity, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        entrySizer.Add(d, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        entrySizer.Add(self.poly, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        entrySizer.Add(plus, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        entrySizer.Add(self.addition, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        entrySizer.Add(keepLabel, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 48)
        entrySizer.Add(self.keep, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        entrySizer.Add(targetLabel, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 20)
        entrySizer.Add(self.target, 0, wx.LEFT|wx.ALIGN_CENTER_VERTICAL, 5)
        
        freeEntrySizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        freeEntrySizer.Add(freeEntryLabel, 0, wx.LEFT|\
        wx.ALIGN_CENTER_VERTICAL, 0)
        freeEntrySizer.Add(self.freeEntry, 0, wx.LEFT|\
        wx.ALIGN_CENTER_VERTICAL, 5)
        freeEntrySizer.Add(self.rollButton, 0, wx.LEFT|\
        wx.ALIGN_CENTER_VERTICAL, 150)
        
        container = wx.BoxSizer(orient=wx.VERTICAL)
        container.Add(topSizer, 0, wx.ALL, 10)
        container.Add(entrySizer, 0, wx.ALL, 10)
        container.Add(freeEntrySizer, 0, wx.ALL, 10)
        container.Add(self.display, 0, wx.ALL, 10)
        panel.SetSizerAndFit(container)
        self.Fit()

    # If the user changes Family, set the contents of the System dropdown
    # appropriately.
    def familyChanged(self, event):
        systemsInThisFamily = \
        families[families.keys()[self.family.GetCurrentSelection()]]
        self.system.Clear()
        for item in systemsInThisFamily:
            self.system.AppendItems([item.name])
        # First time around, System is disabled, so Enable it.
        self.system.Enable(True)
            
    # Here's the main GUI reconfiguration work.  Every time a new System is
    # selected, we need to rearrange the GUI to set fixed things (e.g. World of
    # Darkness must use d10s) and disable unused things (number of keep dice
    # outside of "Roll & Keep" systems).
    def systemChanged(self, event):
        # Get the selected system
        selectedSystem = self.getSelectedSystem()
        
        # Fiddle with GUI things if it's not Free Entry mode.
        if selectedSystem.type != "Free Entry":        
        
            self.freeEntry.Enable(False)
            
            # Enable the Keep box for "Roll & Keep" systems only
            if selectedSystem.type == "Roll & Keep":
                if selectedSystem.fixKeep >= 0:
                    self.keep.SetValue(str(selectedSystem.fixKeep))
                    self.keep.Enable(False)
                else:
                    self.keep.SetValue(self.quantity.GetValue())
                    self.keep.Enable(True)
            else:
                self.keep.SetValue("")
                self.keep.Enable(False)
            
            # Set and Disable the roll quantity if it's fixed.
            if selectedSystem.fixQuantity >= 0:
                self.quantity.SetValue(str(selectedSystem.fixQuantity))
                self.quantity.Enable(False)
            else:
                self.quantity.Enable(True)
            
            # Set and Disable the poly sides if it's fixed.    
            if selectedSystem.fixPoly >= 0:
                self.poly.SetValue(str(selectedSystem.fixPoly))
                self.poly.Enable(False)
            else:
                self.poly.Enable(True)
            
            # Set and Disable the target number if it's fixed.
            if selectedSystem.fixTN >= 0:
                self.target.SetValue(str(selectedSystem.fixTN))
                self.target.Enable(False)
                if selectedSystem.rollOverUnder=="NoTN":
                    self.target.SetValue("")
            else:
                self.target.Enable(True)
            
            # Set and Disable the addition if it's not allowed.
            if selectedSystem.allowAddition == True:
                self.addition.Enable(True)
                self.addition.SetValue("0")  
            else:
                self.addition.Enable(False)
                self.addition.SetValue("")
                
        else:
            self.freeEntry.Enable(True)
            self.quantity.Enable(False)
            self.quantity.SetValue("")
            self.poly.Enable(False)
            self.poly.SetValue("")
            self.addition.Enable(False)
            self.addition.SetValue("")
            self.keep.Enable(False)
            self.keep.SetValue("")
            self.target.Enable(False)
            self.target.SetValue("")
         
    # Roll the dice!
    def rollDice(self, event):
    
        successes = 0
        botches = 0
        self.display.SetValue("")
        
        # Get the selected system (again, we still need it)
        selectedSystem = self.getSelectedSystem()
            
        # Free Entry mode is sufficiently different from the others that we'll
        # handle it separately.
        if selectedSystem.type == "Free Entry":
            calculatedRolls = list()
            calculatedString = ""
            
            # Sanitise free entry string
            lowercaseString = self.freeEntry.GetValue().lower()
            sanitisedString = re.compile("[^0-9d\+\-\*\/\(\)\^]")\
            .sub("",lowercaseString)
            
            # Pull out all the rolls
            rolls = re.compile("\d?d\d+").findall(sanitisedString)
            otherStuff = re.compile("\d?d\d+").split(sanitisedString)
            
            self.display.AppendText("Individual rolls: ")
            
            for roll in rolls:
                dice = list()
                
                # If someone's entered e.g. "d6", make it "1d6"
                if roll[0] == "d":
                    roll = "1" + roll
                    
                # Match the two numbers to obtain quantity and poly
                numbers = re.compile("(\d?)d(\d+)").match(roll)
                quantity = int(numbers.string[numbers.start(1):numbers.end(1)])
                poly = int(numbers.string[numbers.start(2):numbers.end(2)])
                
                self.display.AppendText((" " + roll + ":"))
                
                # Calculate the dice rolls
                for roll in range(0,quantity):
                    dice.append(random.randint(1, poly))
                    
                self.display.AppendText(str(dice))
                
                # Create a nathematical string to replace the roll strings in
                # the user input
                calculatedRoll = "("
                for die in dice:
                    calculatedRoll = calculatedRoll + str(die) + "+"
                calculatedRoll = calculatedRoll[0:len(calculatedRoll)-1] + ")"
                calculatedRolls.append(calculatedRoll)
            
            self.display.AppendText("\n")
            
            # Combine the new calculated rolls with the otherStuff to produce a
            # mathematical formula.
            for i in range(0,len(calculatedRolls)):
                calculatedString = calculatedString + otherStuff[i] \
                + calculatedRolls[i]
            calculatedString = calculatedString + otherStuff[len(otherStuff)-1]
            
            # Calculate and print total
            total = eval(calculatedString)
            string = "Total: " + str(total) + "\n"
            self.display.AppendText(string)
                
        else:
            # Roll up an initial set of dice
            dice = list()
            for die in range(int(self.quantity.GetValue())):
                dice.append(random.randint(1, int(self.poly.GetValue())))
                
            # Count minimums and maximums
            minimums = len(filter(lambda x : x==1, dice))
            maximums = len(filter(lambda x : x==\
            int(self.poly.GetValue()), dice))
            
            # Count botches
            if selectedSystem.minIsBotch == True:
                botches = minimums
            
            # Calculations for the Overall Target family
            if selectedSystem.type == "Overall Target":
            
                # Calculate explosions
                if selectedSystem.maxExplodes == True:
                    dice = self.explodeOverall(dice)
                    
                # Display individual rolls
                string = "Individual rolls: " + str(dice) + "\n"
                self.display.AppendText(string)
                
                # Calculate the sum of the dice
                total = reduce(lambda x,y : x+y, dice)
                
                # Add an addition value if it exists
                if selectedSystem.allowAddition == True:
                    total = total + int(self.addition.GetValue())
                string = "Total: " + str(total) + "\n"
                self.display.AppendText(string)
                
                # If there's a target to beat, compare against it.
                if selectedSystem.rollOverUnder != "NoTN":
                    if total < int(self.target.GetValue()):
                        self.display.AppendText("Rolled less than target.\n")
                        if selectedSystem.rollOverUnder == "Under":
                            successes = successes + 1
                            
                    if total > int(self.target.GetValue()):
                        self.display.AppendText("Rolled more than target.\n")
                        if selectedSystem.rollOverUnder == "Over":
                            successes = successes + 1
                            
                    if total == int(self.target.GetValue()):
                        self.display.AppendText("Rolled even with target.\n")
                        successes = successes + 1
                    
                    # Make maxes a success even if TN > max
                    if selectedSystem.maxIsSuccess == True:
                        if (successes == 0 and maximums > 0):
                            successes = maximums
                    
                    # Print result
                    if successes > 0:
                        self.display.AppendText("Success!\n")
                    else:
                        if botches > 0:
                            self.display.AppendText("Botch.\n")
                        else:
                            self.display.AppendText("Failure.\n")


            # Calculations for the Success-Based family
            if selectedSystem.type == "Success-based":
            
                # Calculate explosions
                if selectedSystem.maxExplodes == True:
                    dice = self.explodeSuccessBased(dice,0)
                    
                # Display individual rolls
                string = "Individual rolls: " + str(dice) + "\n"
                self.display.AppendText(string)
                
                # Count successes
                if selectedSystem.rollOverUnder == "Over":
                    successes = len(filter(lambda x : x>=\
                    int(self.target.GetValue()), dice))
                else:
                    successes = len(filter(lambda x : x<=\
                    int(self.target.GetValue()), dice))

                # Make maxes a success even if TN > max
                if selectedSystem.maxIsSuccess == True:
                    if (successes == 0 and maximums > 0):
                        successes = maximums

                # Double max-values if required
                if selectedSystem.maxIsDouble == True:
                    successes = successes + maximums

                # Subtract mins from successes if required
                if selectedSystem.minIsMinusSuccess == True:
                    successes = successes - minimums
                
                # Print result
                if successes > 0:
                    string = "%d successes!\n" % successes
                    self.display.AppendText(string)
                else:
                    if botches > 0:
                        self.display.AppendText("Botch.\n")
                    else:
                        self.display.AppendText("No successes.\n")
                    
            if selectedSystem.type == "Roll & Keep":
            
                # Calculate explosions
                if selectedSystem.maxExplodes == True:
                    dice = self.explodeOverall(dice)
                    
                # Display individual rolls
                string = "Individual rolls: " + str(dice) + "\n"
                self.display.AppendText(string)
                
                # Keep a certain number of dice, lowest ones for "Under" TN,
                # highest ones for "Over" TN or "NoTN".
                if selectedSystem.rollOverUnder == "Under":
                    dice.sort(reverse=False)
                else:
                    dice.sort(reverse=True)
                dice = dice[0:int(self.keep.GetValue())]
                
                # Display chosen rolls
                string = "Chosen rolls: " + str(dice) + "\n"
                self.display.AppendText(string)
                
                # Calculate the sum of the dice
                total = reduce(lambda x,y : x+y, dice)
                string = "Total: " + str(total) + "\n"
                self.display.AppendText(string)
                
                # If there's a target to beat, compare against it.
                if selectedSystem.rollOverUnder != "NoTN":
                    if total < int(self.target.GetValue()):
                        self.display.AppendText("Rolled less than target.\n")
                        if selectedSystem.rollOverUnder == "Under":
                            successes = successes + 1
                            
                    if total > int(self.target.GetValue()):
                        self.display.AppendText("Rolled more than target.\n")
                        if selectedSystem.rollOverUnder == "Over":
                            successes = successes + 1
                            
                    if total == int(self.target.GetValue()):
                        self.display.AppendText("Rolled even with target.\n")
                        successes = successes + 1
                        
                    # Print result
                    if successes > 0:
                        self.display.AppendText("Success!\n")
                    else:
                        self.display.AppendText("Failure.\n")

            
    # Returns the instance of System that has been chosen with the drop-downs.
    def getSelectedSystem(self):
        systemsInThisFamily = \
        families[families.keys()[self.family.GetCurrentSelection()]]
        selectedSystemName = \
        str(systemsInThisFamily[self.system.GetCurrentSelection()])
        selectedSystem = \
        filter(lambda x : (x.name==selectedSystemName), systems)[0]
        return selectedSystem
        
        
    # Recursively calculate dice explosions (Success-based style)
    def explodeSuccessBased(self,dice,startFrom):
        newExplosions = 0
        length = len(dice)
        newDice = dice[startFrom:length]
        for die in newDice:
            if die == int(self.poly.GetValue()):
                dice.append(random.randint(1, int(self.poly.GetValue())))
                newExplosions = newExplosions + 1
        if newExplosions > 0:
            dice = self.explodeSuccessBased(dice,length)
        return dice
        
        
    # Recursively calculate dice explosions (Overall Target and Roll & Keep
    # style)
    def explodeOverall(self,dice):
        newDice = list()
        newExplosions = 0
        for die in dice:
            # If die value is a multiple of poly max...
            if die%int(self.poly.GetValue()) == 0:
                die = die + random.randint(1, int(self.poly.GetValue()))
                newExplosions = newExplosions + 1
            newDice.append(die)
        if newExplosions > 0:
            newDice = self.explodeOverall(newDice)
        return newDice


# Main app class
class Roller(wx.App):
    def OnInit(self):
        frame = MainFrame(None, -1, "RPG Dice Roller")
        frame.Show(True)
        self.SetTopWindow(frame)
        return True


# Add systems here.  They will be added to the menu automatically.  Each system
# takes parameters as defined in the System class above.
#    name,family,type,fixQuantity,fixPoly,fixKeep,fixTN,rollOverUnder,
#    minIsBotch,minIsMinusSuccess,maxExplodes,maxIsDouble,maxIsSuccess,
#    allowAddition
systems = list()
systems.append(System("1d20 Attempt", "d20", "Overall Target", 1, 20, -1, -1, "Over", True, False, True, False, True, False))
systems.append(System("Basic Roll", "d20", "Overall Target", -1, -1, -1, 0, "NoTN", False, False, False, False, False, True))
systems.append(System("Free Entry", "Miscellaneous", "Free Entry", -1, -1, -1, -1, "NoTN", False, False, False, False, False, False))
systems.append(System("Shadowrun 3rd Ed", "Shadowrun", "Overall Target", -1, 6, -1, -1, "Over", False, False, True, False, False, False))
systems.append(System("Shadowrun 3rd Ed (Open Test)", "Shadowrun", "Roll & Keep", -1, 6, 1, 0, "NoTN", False, False, True, False, False, False))
systems.append(System("World of Darkness 1st Ed", "White Wolf", "Success-based", -1, 10, -1, -1, "Over", True, True, True, False, False, False))
systems.append(System("World of Darkness 2nd Ed", "White Wolf", "Success-based", -1, 10, -1, -1, "Over", True, True, False, False, False, False))
systems.append(System("World of Darkness 2nd Ed (Specialised)", "White Wolf", "Success-based", -1, 10, -1, -1, "Over", True, True, True, False, False, False))
systems.append(System("World of Darkness 3rd Ed", "White Wolf", "Success-based", -1, 10, -1, -1, "Over", True, False, False, False, False, False))
systems.append(System("World of Darkness 3rd Ed (Specialised)", "White Wolf", "Success-based", -1, 10, -1, -1, "Over", True, False, True, False, False, False))
systems.append(System("New World of Darkness", "White Wolf", "Success-based", -1, 10, -1, 8, "Over", False, False, True, False, False, False))
systems.append(System("New World of Darkness (Chance Die)", "White Wolf", "Success-based", 1, 10, -1, 10, "Over", True, False, True, False, False, False))
systems.append(System("Exalted 1st Ed", "White Wolf", "Success-based", -1, 10, -1, 7, "Over", True, False, False, True, False, False))
systems.append(System("7th Sea", "Roll & Keep", "Roll & Keep", -1, 10, -1, -1, "Over", False, False, True, False, False, False))
systems.append(System("Legend of the Five Rings", "Roll & Keep", "Roll & Keep", -1, 10, -1, -1, "Over", False, False, True, False, False, False))

families = dict()
for system in systems:
    if not (system.family in families):
        families[system.family] = list()
    families[system.family].append(system)


app = Roller(0)
app.MainLoop()

