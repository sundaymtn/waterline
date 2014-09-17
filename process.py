'''
@author: scarter
'''
import subprocess
import re
import logging
import time

class ProcessClass(object):
    ### TODO smcarter document fail text and free pass
    '''Run an external process via subprocess and handle the output

    Attributes:
        out (boolean): print the output to the console
        environ (dictionary): optional dictionary of environment vars needed by process
        use_call (boolean): use subprocess call instead of Popen
        exec_list (list): list of 1 or more cmds to be executed
        return_proc (boolean): return the process id once the process is started
        limit_response (int): number of lines to limit the returned output to, 0 for unlimited
        errors_expected (boolean): return successful even if errors are encountered

    Example:
        e = process.ProcessClass(
                                exec_list = ([r'echo %RESPONSE%', ],),
                                out = 1,
                                limit_response = 0,
                                errors_expected = 0,
                                return_proc = 0,
                                use_call = 0,
                                environ = {"RESPONSE": "Custom Environment Response"}
                                )
        e.execute()
        >>>Running   echo %RESPONSE%
        >>>Custom Environment Response
    '''


    def __init__(self, exec_list=[], out=True, environ=None, use_call=False, use_shell=True,
                 limit_response=0, return_proc=False, errors_expected=False, free_pass=None, fail_texts=None):
        '''Inits ProcessClass with supplied attributes'''
        self.out = out
        self.err_string = ''
        self.environ = environ
        self.use_call = use_call
        self.use_shell = use_shell
        self.local_response = []
        self.exec_list = exec_list
        self.return_proc = return_proc
        self.limit_response = limit_response
        self.errors_expected = errors_expected
        self.free_pass = []
        self.fail_texts = [' error ', 'does not exist', 'insufficient privileges',
                  'logon denied', 'error:',
                  'is not recognized as an internal or external command',
                  'Invalid command:',
                  "can't open file",
                  'ERROR',
                  'No such file or directory',
                  'The system cannot find the path specified',
                  'command not found'
                  ]
        if free_pass:
            self.free_pass.extend(free_pass)
        if fail_texts:
            self.fail_texts.extend(fail_texts)

    def execute(self,):
        '''executes the supplied cmd(s) with subprocess'''
        for cmd in self.exec_list:
            if self.out:
                logging.info('Running  ' + ' '.join(cmd))
            if self.use_call:
                return subprocess.call(cmd,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      stdin=subprocess.PIPE,
                                      env=self.environ,
                                      shell=self.use_shell)
            else:
                proc = subprocess.Popen(cmd,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        stdin=subprocess.PIPE,
                                        env=self.environ,
                                        shell=self.use_shell)
            if self.return_proc:
                return proc
            stdout_value = proc.communicate()
            limit_ctr = self.limit_response
            for value in stdout_value:
                response = value.split('\n')
                for r in response:
                    if [err for err in self.fail_texts if err and re.search(err, r)]:
                        if self.errors_expected or [err for err in self.free_pass if re.search(err, r)]:
                            pass
                        else:
                            self.err_string = '\n'.join(response[response.index(r):])
                            raise Warning('Error text detected on following line(s):\n' + self.err_string)
                    if self.limit_response == 0 or limit_ctr:
                        if r:
                            self.local_response.append(r)
                            limit_ctr -= 1
                    if self.out:
                        if r:
                            logging.info(r)
        return self.local_response
    
    def tskill(self, proc_name):
        if self.underlying_os_windows:
            proc = self.ProcessClass(exec_list=(['tasklist'],), out=False)
            tasklist = proc.execute()
            for t in tasklist:
                m = re.search('(' + proc_name + ')(.*)(Console|RDP-Tcp#\d)', t)
                if m:
                    logging.info('Found running: ' + m.group(0))
                    pid = m.group(2).strip()
                    proc = self.ProcessClass(exec_list=(['taskkill', '/PID', pid, '/F'],), out=True)
                    tasklist = proc.execute()
                    time.sleep(1)
        if self.underlying_os_linux:
            proc = self.ProcessClass(exec_list=([' ps -ef | grep ' + self.user],), out=False)
            tasklist = proc.execute()
            for t in tasklist:
                logging.debug('task ' + t)
                m = re.search(self.user + '\s{1,}(\d{1,})\s.*?' + proc_name, t)
                if m:
                    logging.info('Found running: ' + m.group(0))
                    pid = m.group(1).strip()
                    proc = self.ProcessClass(exec_list=(['kill -9 ' + pid],), out=True)
                    tasklist = proc.execute()
                    time.sleep(1)    
