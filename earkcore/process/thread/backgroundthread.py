import threading
import time


class BackgroundThread(object):
    """
    Run a method passed as a parameter by the constructor as a background thread.
    """

    def __init__(self, backgroundfunc, kwargs={}):

        """ Constructor
        :type backgroundfunc: function
        :param backgroundfunc: Function to be executed in background
        """
        print "BackgroundThread started (%s)" % backgroundfunc.__name__

        self.backgroundfunc = backgroundfunc
        self.kwargs = kwargs

        thread = threading.Thread(target=self.run, args=())
        thread.daemon = True
        thread.start()

    def run(self):
        self.backgroundfunc(self.kwargs)
