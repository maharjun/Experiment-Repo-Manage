from cmd import Cmd
import os
import shlex
import re
import textwrap
import BasicUtils as BU
from BasicUtils import errprint, conprint
import Entities
from git import Repo
from enum import Enum
import BookIDs
import sys
from io import StringIO


class PromptStatus(Enum):
    """
    This class (an enumeration) defines various values to define the
    state of the console.
    """
    EXIT          = 1 << 0
    INVALID_ARG   = 1 << 1
    SUCCESS       = 1 << 2
    ITER_OVER     = 1 << 3


class RepoManageConsole(Cmd):
    intro = 'Welcome to the Repositry Management shell. Type help or ? to list commands.'
    prompt = 'command> '
    
    TopLevelDir = ''
    ThisModuleDir = ''
    NewEntityData = []
    CurrentEntityData = []
    
    ValidCommandList = ['book', 'unbook', 'list', 'clear', 'confirm', 'restart', 'exit']
    
    # This is a Flag. If it is set, then any call to exit will exit
    # without saving the session. This cannot be set by any command.
    # it can only be set when, during the execution of one of the
    # commands, we encounter an error in which we require to terminate
    # the prompt but result saving would be undefined.
    SaveSession = True
    
    # This flag indicates whether the preloop initialization went
    # smoothly. It is assumed to be true and is set to false in the
    # preloop function if initialization fails.
    InitSuccessful = True
    
    # This is a Flag. It indicates whether a redirection is desired
    # in the current function call. If it is true, the value of
    # RedirFile is used to provide the redirection
    isRedirNeeded = False
    RedirFilePath = ""
    
    # TTD:
    # Find out the variables that need to be global
    
    # ----- Top Level Interface commands -----
    def do_book(self, arg):
        """\
        This comand is used to BOOK AN ENTITY, The following is the format
        of the expected input:
          
          book <dir|exp> <Path> [--n<number>] [--inter] [--force] [--reltop] [--noconf]
        
        Here, The paramters are:
          
          <dir|exp>   -- [MANDATORY parameter] Used to specify if one wishes to book
                         a dir(ectory) or some exp(eriments). This MUST be the first
                         argument after 'book'.
          
          <Path>      -- [MANDATORY parameter] The path of the given directory. the
                         path can be either relative to the current directory or the
                         top level directory of Experiments repository. The position
                         of this option must be after the <dir|exp> parameter.
          
          --n<number> -- This option is only valid in the case of booking experiments.
                         It will be ignored otherwise. It specifies the number of
                         experiments to book in the specified path. Defaults to 1 if
                         not specified.
          
          --inter     -- This forces the given directory to be booked as an inter-
                         mediate directory as opposed to an experiment directory
                         (which is the default)
          
          --force     -- Enable Forced Booking (i.e. book IDs for all subdirectories
                         leading to the final directory if they havent been previously
                         booked.
          
          --reltop    -- Indicates that the path mentioned is not relative to the
                         current working directory, but rather, the path relative to
                         the base of the repository
          
          --noconf    -- This option instructs the program to not request for conf-
                         irmation of input.
        """
        
        Status = PromptStatus.SUCCESS
        
        Args = shlex.split(arg)
        
        if not Args:
            errprint("You must enter atleast 2 arguments (see help)")
            Status = PromptStatus.INVALID_ARG
        
        Force = False
        RelativetoTop = False
        Type = ''
        isDirectory = False
        NeedConf = True
        NumExps = 1
        Path = ''
        
        if Args[0] == 'dir':
            Type = 'ExperimentDir'
            isDirectory = True
        elif Args[0] == 'exp':
            Type = 'Experiment'
            isDirectory = False
        else:
            errprint('The first argument must either be "dir" or "exp". (Look at help)')
            Status = PromptStatus.INVALID_ARG
        
        if Status == PromptStatus.SUCCESS:
            for arg in Args[1::]:
                if arg.startswith('--'):
                    if arg == '--force':
                        Force = True
                    elif arg == '--reltop':
                        RelativetoTop = True
                    elif arg == '--inter' and isDirectory:
                        Type = 'IntermediateDir'
                    elif arg == '--noconf':
                        NeedConf = False
                    elif re.match(r"--n[0-9]+", arg):
                        NumExps = int(arg[3:])
                        if NumExps == 0:
                            errprint("The number of experiments to bee booked must be > 0")
                            Status = PromptStatus.INVALID_ARG
                    else:
                        errprint("Invalid Option {Arg}\n. Look at help.".format(Arg=arg))
                        Status = PromptStatus.INVALID_ARG
                        break
                elif not Path:
                    Path = arg
                else:
                    errprint("Unable to make sense of argument '{Arg}'".format(Arg=arg))
                    Status = PromptStatus.INVALID_ARG
                    break
        
        if Path and BU.isValidPathRE.match(Path):
            try:
                Path = BU.ProcessPath(Path, self.TopLevelDir, RelativetoTop)
            except ValueError:
                errprint("It appears as though the directory was invalid\n")
                Status = PromptStatus.INVALID_ARG
                BookingSuccess = False
        elif Path:
            errprint("The Path {Path} is invalid. Paths must satisfy the following regex\n".format(Path=Path))
            errprint(BU.isValidPathREStr)
            Status = PromptStatus.INVALID_ARG
        else:
            errprint("Path to be booked hasn't been specified\n")
            Status = PromptStatus.INVALID_ARG
        
        if Status == PromptStatus.SUCCESS and NeedConf:
            if isDirectory:
                conprint(textwrap.dedent(("""
                    Please confirm your input (confirm: capital Y, not confirm: anything else)
                      
                      Path          : {Path}
                      Type          : {Type}
                      
                      Force         : {Force}
                    
                    """).format(Path=Path,Type=Type,Force=Force)))
                Confirmation = BU.getNonEmptyInput(">> ")
                if Confirmation in ['y', 'Y']:
                    Status = PromptStatus.SUCCESS
                else:
                    conprint("Booking Cancelled")
                    Status = PromptStatus.ITER_OVER
            else:
                conprint(textwrap.dedent(("""
                    Please confirm your input (confirm: capital Y, not confirm: anything else)
                      
                      Path               : {Path}
                      Type               : {Type}
                      No. of Experiments : {NExp}
                      
                      Force              : {Force}
                    
                    """).format(Path=Path,Type=Type,Force=Force,NExp=NumExps)))
                Confirmation = BU.getNonEmptyInput(">> ")
                if Confirmation in ['y', 'Y']:
                    Status = PromptStatus.SUCCESS
                else:
                    print("Booking Cancelled")
                    Status = PromptStatus.ITER_OVER
        
        if Status == PromptStatus.SUCCESS:
            if isDirectory:
                BookingSuccess = BookIDs.BookDirectory(
                    Path, Type,
                    self.NewEntityData, self.CurrentEntityData,
                    Force=Force)
                
                if BookingSuccess:
                    print("The following booking was successful:\n")
                    print("  Path: {Path}".format(Path=Path))
                    print("  Type: {Type}\n".format(Type=Type))
                else:
                    errprint("The following booking was unsuccessful\n")
                    errprint("  Path: {Path}".format(Path=Path))
                    errprint("  Type: {Type}\n".format(Type=Type))
                    Status = PromptStatus.INVALID_ARG
            else:
                BookingSuccess = BookIDs.BookExperiments(
                        Path, self.NewEntityData, self.CurrentEntityData,
                        NumofExps=NumExps, Force=Force)
                
                if BookingSuccess:
                    print("The following booking was successful:\n")
                    print("  Path: {Path}".format(Path=Path))
                    print("  Type: {Type}".format(Type=Type))
                    print("  NExp: {NExp}\n".format(NExp=NumExps))
                else:
                    errprint("The following booking was unsuccessful\n")
                    errprint("  Path: {Path}".format(Path=Path))
                    errprint("  Type: {Type}".format(Type=Type))
                    errprint("  NExp: {NExp}\n".format(NExp=NumExps))
                    Status = PromptStatus.INVALID_ARG
    
    def do_unbook(self, arg):
        # Do unbooking here
        """\
        This command is used to UNBOOK AN ENTITY, The following is the format
        of the expected input:
          
          unbook <dir|exp> <Path> [--n<number>] [--force] [--reltop] [--noconf]
        
        Here, The paramters are:
          
          <dir|exp>   -- [MANDATORY parameter] Used to specify if one wishes to
                         unbook a dir(ectory) or some exp(eriments). This MUST be the
                         first argument after 'unbook'.
          
          <Path>      -- [MANDATORY parameter] The path of the given directory. the
                         path can be either relative to the current directory or the
                         top level directory of Experiments repository. The position
                         of this option must be after the <dir|exp> parameter.
          
          --n<number> -- This option is only valid in the case of unbooking experi-
                         ments. It will be ignored otherwise. It specifies the number
                         of experiments to unbook in the specified path. Defaults to
                         1 if not specified.
          
          --force     -- Enable Forced UnBooking (i.e. unbook the current directory and
                         all children). The default behaviour is to exit with a warning
                         if a directory has children.
          
          --reltop    -- Indicates that the path mentioned is not relative to the
                         current working directory, but rather, the path relative to
                         the base of the repository
          
          --noconf    -- This option instructs the program to not request for conf-
                         irmation of input.
        """
        
        Status = PromptStatus.SUCCESS
        
        Args = shlex.split(arg)
        
        if not Args:
            errprint("You must enter atleast 2 arguments (see help)")
            Status = PromptStatus.ITER_OVER
        
        Force = False
        RelativetoTop = False
        isDirectory = False
        NeedConf = True
        NumExps = 1
        Path = ''
        
        if Args[0] == 'dir':
            isDirectory = True
        elif Args[0] == 'exp':
            isDirectory = False
        else:
            errprint('The first argument must either be "dir" or "exp". (Look at help)')
            Status = PromptStatus.ITER_OVER
        
        if Status == PromptStatus.SUCCESS:
            for arg in Args[1::]:
                if arg.startswith('--'):
                    if arg == '--force':
                        Force = True
                    elif arg == '--reltop':
                        RelativetoTop = True
                    elif arg == '--noconf':
                        NeedConf = False
                    elif re.match(r"--n[0-9]+", arg):
                        NumExps = int(arg[3:])
                    else:
                        errprint("Invalid Option {Arg}\n. Look at help.".format(Arg=arg))
                        Status = PromptStatus.INVALID_ARG
                        break
                elif not Path:
                    Path = arg
                else:
                    errprint("Unable to make sense of argument '{Arg}'".format(Arg=arg))
                    Status = PromptStatus.INVALID_ARG
                    break
        
        if Path and BU.isValidPathRE.match(Path):
            try:
                Path = BU.ProcessPath(Path, self.TopLevelDir, RelativetoTop)
            except ValueError:
                errprint("It appears as though the directory was invalid\n")
                Status = PromptStatus.INVALID_ARG
        
        elif Path:
            errprint("The Path {Path} is invalid. Paths must satisfy the following regex\n".format(Path=Path))
            errprint(BU.isValidPathREStr)
            Status = PromptStatus.INVALID_ARG
        else:
            errprint("Path to be booked hasn't been specified\n")
            Status = PromptStatus.INVALID_ARG
        
        if Status == PromptStatus.SUCCESS and NeedConf:
            if isDirectory:
                conprint(textwrap.dedent(("""
                    Please confirm your input (confirm: Y, not confirm: anything else)
                      
                      Path          : {Path}
                      
                      Force         : {Force}
                    
                    """).format(Path=Path,Force=Force)))
                Confirmation = BU.getNonEmptyInput(">> ")
                if Confirmation in ['y', 'Y']:
                    Status = PromptStatus.SUCCESS
                else:
                    print("Booking Cancelled")
                    Status = PromptStatus.ITER_OVER
            else:
                conprint(textwrap.dedent(("""
                    Please confirm your input (confirm: capital Y, not confirm: anything else)
                      
                      Path               : {Path}
                      No. of Experiments : {NExp}
                      
                      Force              : {Force}
                    
                    """).format(Path=Path,Force=Force,NExp=NumExps)))
                Confirmation = BU.getNonEmptyInput(">> ")
                if Confirmation in ['y', 'Y']:
                    Status = PromptStatus.SUCCESS
                else:
                    print("Booking Cancelled")
                    Status = PromptStatus.ITER_OVER
        
        if Status == PromptStatus.SUCCESS:
            if isDirectory:
                UnBookingSuccess = BookIDs.UnBookDirectory(
                                        Path, self.NewEntityData,
                                        Force=Force)
                
                if UnBookingSuccess:
                    print("The following Directory (and children) were successfully unbooked:\n")
                    print("  Path: {Path}\n".format(Path=Path))
                else:
                    errprint("The following unbooking was unsuccessful\n")
                    errprint("  Path: {Path}".format(Path=Path))
                    Status = PromptStatus.INVALID_ARG
            else:
                UnBookingSuccess = BookIDs.UnBookExperiments(
                            Path, self.NewEntityData,
                            NumofExps=NumExps)
                
                if UnBookingSuccess:
                    print("The following experiments were successfully unbooked:\n")
                    print("  Path: {Path}".format(Path=Path))
                    print("  NExp: {NExp}\n".format(NExp=NumExps))
                else:
                    errprint("The following booking was unsuccessful\n")
                    errprint("  Path: {Path}".format(Path=Path))
                    errprint("  NExp: {NExp}\n".format(NExp=NumExps))
                    Status = PromptStatus.INVALID_ARG
    
    def do_list(self, arg):
        # Do listing here
        """
        This command takes no arguments. It simply outputs (in heirarchial format),
        the directories and experiments that have been booked in the current session,
        (i.e. booked and not yet confirmed).
        """
        print(BookIDs.getSessionBookingsString(self.NewEntityData))
    
    def do_clear(self, arg):
        """
        Command syntax
          
          clear [--noconf]
        
        This command is used to clear the current booking session. i.e. all the
        booked entities that have no been confirmed will be unbooked. It will ask
        for a confirmation unless --noconf is specified.
        """
        
        Status = PromptStatus.SUCCESS
        Args = shlex.split(arg)
        ConfNeeded = True
        if Args:
            for arg in Args:
                if arg == '--noconf':
                    ConfNeeded = False
                else:
                    errprint("Invalid option (see help): {Option}".format(Option=arg))
                    Status = PromptStatus.INVALID_ARG
                    break
        
        if Status == PromptStatus.SUCCESS and ConfNeeded:
            ConfirmationStr = BU.getNonEmptyInput("You Sure? (Y/n): ")
            if ConfirmationStr not in ['y', 'Y']:
                Status = PromptStatus.ITER_OVER
        
        if Status == PromptStatus.SUCCESS:
            self.NewEntityData = []
    
    def do_confirm(self, arg):
        """
        Command syntax:
          
          confirm [--noconf]
        
        This command is to confirm the bookings in the current session. i.e. all the
        entities (directories/experiments) booked in the current session will be
        committed. The list command will be invoked for confirmation unless --noconf
        is specified.
        """
        
        # print the listing of the bookings
        conprint(BookIDs.getSessionBookingsString(self.NewEntityData))
        
        Args = shlex.split(arg)
        ConfNeeded = True
        if Args and Args[0] == '--noconf':
            ConfNeeded = False
        elif Args:
            errprint("\nInvalid Argument {Arg}".format(Arg=Args[0]))
            return
        
        isConfirmed = True
        if ConfNeeded:
            Confirmation = BU.getNonEmptyInput("You Sure you want to commit the above (Y/n)? ")
            if Confirmation not in ['y', 'Y']:
                isConfirmed = False
        
        if isConfirmed:
            isBookingsConfirmed = BookIDs.ConfirmBookings(
                self.CurrentEntityData,
                self.NewEntityData,
                Repo(self.TopLevelDir))
            if isBookingsConfirmed:
                # perform a restart to update the Datas and CurrentSession.yml
                self.CurrentEntityData.append(self.NewEntityData)
                self.NewEntityData = []
                # Perform Restart (to update CurrentSession.yml)
                self.do_restart("")
            # else:
            #     Do nothing
    
    def precmd(self, line):
        """
        This function processes each line before passing it to the commands.
        Currently this function performs the following function:
        
        It analyses the line for any specified output redirection and enables
        said redirection before running the command.
        """
        
        # split the line. This also tests if the line is validly splittable
        try:
            Args = shlex.split(line)
        except ValueError as V:
            errprint("\nUnknown Syntax see below for more details:")
            print("")
            print(V.args[0])
            line = ""
            Args = []

        # check if redirection is requested and calculate position of '>'
        isRedir = ('>' in Args)
        RedirIndex = Args.index('>') if isRedir else None
        
        isValidRedir = True
        
        if isRedir:
            # Validate Redirection
            # 1. Ensure that '>' is the second last argument
            if (RedirIndex == len(Args)-2):
                RedirPath = Args[-1]
            else:
                errprint(
                    "\nExactly 1 argument expected after output redirection marker '>'"
                )
                isValidRedir = False
            
            if isValidRedir:
                # if it is valid, Enable Redirection, store path and
                # clip redirection from line
                self.isRedirNeeded = isRedir
                self.RedirFilePath = RedirPath
                line = " ".join(Args[0:-2])
            else:
                # make line blank so that no command is executed
                line = ""
        
        return line
    
    def onecmd(self, line):
        """
        This function adds some exception handling in the context of the stream
        redirection operations.
        """
        
        if self.isRedirNeeded:
            TempStream = StringIO()
            sys.stdout = TempStream
            try:
                RetValue = Cmd.onecmd(self, line)
                OutputString = TempStream.getvalue()
                try:
                    with open(self.RedirFilePath, 'w') as Fout:
                        Fout.write(OutputString)
                except:
                    errprint(
                        "\nError writing stdout to file {0}".format(self.RedirFilePath)
                    )
            finally:
                TempStream.close()
                sys.stdout = sys.__stdout__
        else:
            RetValue = Cmd.onecmd(self, line)

        return RetValue
    
    def postcmd(self, stop, line):
        self.isRedirNeeded = False
        self.RedirFilePath = ""
        return super().postcmd(stop, line)

    def preloop(self):
        self.ThisModuleDir = BU.getFrameDir()
        self.TopLevelDir = os.path.normpath(os.path.join(self.ThisModuleDir, '..'))
        
        # Read Currently confirmed Entity Data
        CurrEntityDataFile = os.path.join(self.TopLevelDir, 'EntityData.yml')
        if os.path.isfile(CurrEntityDataFile):
            with open(CurrEntityDataFile, 'r') as Fin:
                self.CurrentEntityData = BookIDs.getEntityDataFromStream(Fin)
        else:
            errprint('The file EntityData.yml is missing')
            self.CurrentEntityData = None
        
        # See if read was successful
        if self.CurrentEntityData is None:
            errprint(
                'It appears that we cannot read the urrently booked Entities\n',
                'from the file {0}. INITIALIZATION FAILED\n'.format('EntityData.yml')
            )
            self.InitSuccessful = False
        
        # try to read the Current Session (new unconfirmed) Entities
        NewEntityDataFile  = os.path.join(self.ThisModuleDir, 'TempFiles/CurrentSession.yml')
        if self.InitSuccessful and os.path.isfile(NewEntityDataFile):
            with open(NewEntityDataFile, 'r') as Fin:
                self.NewEntityData = BookIDs.getEntityDataFromStream(Fin)
        else:
            self.NewEntityData = []
        
        if self.NewEntityData is None:
            errprint(
                'It appears that we cannot read the currently uncommitted Entities\n',
                'from the file {0}. INITIALIZATION FAILED\n'.format('CurrentSession.yml'))
            self.InitSuccessful = False
        
        # if the initialization is not successful, call exit without saving
        if not self.InitSuccessful:
            self.SaveSession = False
            self.intro = ''
            self.cmdqueue.append('exit')
    
    def emptyline(self):
        """
        This is the method called when the imput is an empty line.
        Here we do absolutely nothing
        """
        
        return False  # i.e. dont terminate console
    
    def default(self, line):
        Args = shlex.split(line)
        Command = Args[0]
        errprint("The command '{Cmd}' is undefined\n".format(Cmd=Command))
        self.do_help([])
    
    def do_help(self, arg):
        'List available commands with "help" or detailed help with "help cmd".'
        if arg:
            # if arg is specified then display help for the command specified in arg.
            if arg in self.ValidCommandList:
                doc = getattr(self, "do_" + arg).__doc__
                self.stdout.write(textwrap.dedent("%s\n" % str(doc)))
            else:
                self.stdout.write("The function '%s' is not defined.\n\n" % arg)
            return
        else:
            # if arg is not specified display the default Cmd help instructions
            Cmd.do_help(self, [])
    
    def do_restart(self, arg):
        """
        Command Syntax:
            
            restart
        
        This is equivalent to running exit and starting the console again.
        This has the result of updating CurrentSession.yml with the new
        NewEntityData without having to close the console
        """
        
        conprint('\n(Saving current session)')
        TempFilesDir = os.path.join(self.ThisModuleDir, 'TempFiles')
        if not os.path.isdir(TempFilesDir):
            os.mkdir(TempFilesDir)
        with open(os.path.join(TempFilesDir, 'CurrentSession.yml'), 'w') as Fout:
            Entities.FlushData(Fout, self.NewEntityData)
        
        conprint('(Restarting)')
        self.preloop()
    
    def do_exit(self, arg):
        'Exit (Saving current session)'
        
        if self.SaveSession:
            conprint('(Saving current session)')
            TempFilesDir = os.path.join(self.ThisModuleDir, 'TempFiles')
            if not os.path.isdir(TempFilesDir):
                os.mkdir(TempFilesDir)
            with open(os.path.join(TempFilesDir, 'CurrentSession.yml'), 'w') as Fout:
                Entities.FlushData(Fout, self.NewEntityData)
        conprint('(Exiting)')
        return True

if __name__ == '__main__':
    RepoManageConsole().cmdloop()
