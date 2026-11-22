class AnswerLostError(Exception):
    """The line closed after a request went out but before its answer came: the program may have done it, so
    it is not sent again (that could do it twice). Not a ConnectionError on purpose."""
