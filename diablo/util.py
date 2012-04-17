#  -*- coding: utf-8 -*-
# util.py ---
#
# Created: Fri Dec 30 23:27:52 2011 (+0200)
# Author: Janne Kuuskeri
#


import re
from xml.sax.saxutils import XMLGenerator

charset_pattern = re.compile('.*;\s*charset=(.*)')


def camelcase_to_slash(name):
    """ Converts CamelCase to camel/case

    code ripped from http://stackoverflow.com/questions/1175208/does-the-python-standard-library-have-function-to-convert-camelcase-to-camel-cas
    """

    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1/\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1/\2', s1).lower()


def strip_charset(content_type):
    """ Strip charset from the content type string.

    :param content_type: The Content-Type string (possibly with charset info)
    :returns: The Content-Type string without the charset information
    """

    return content_type.split(';')[0]


def extract_charset(content_type):
    """ Extract charset info from content type.

    E.g.  application/json;charset=utf-8  ->  utf-8

    :param content_type: The Content-Type string (possibly with charset info)
    :returns: The charset or ``None`` if not found.
    """

    match = charset_pattern.match(content_type)
    return match.group(1) if match else None

def get_charset(request):
    """ Extract charset from the content type
    """

    content_type = request.getHeader('content-type') or None
    if content_type:
        return extract_charset(content_type) if content_type else None
    else:
        return None


def parse_accept_header(accept):
    """ Parse the Accept header

    todo: memoize

    :returns: list with pairs of (media_type, q_value), ordered by q
    values.
    """

    def parse_media_range(accept_item):
        """ Parse media range and subtype """

        return accept_item.split('/', 1)

    def comparator(a, b):
        """ Compare accept items a and b """

        # first compare q values
        result = -cmp(a[2], b[2])
        if result is not 0:
            # q values differ, no need to compare media types
            return result

        # parse media types and compare them (asterisks are lower in precedence)
        mtype_a, subtype_a = parse_media_range(a[0])
        mtype_b, subtype_b = parse_media_range(b[0])
        if mtype_a == '*' and subtype_a == '*':
            return 1
        if mtype_b == '*' and subtype_b == '*':
            return -1
        if subtype_a == '*':
            return 1
        if subtype_b == '*':
            return -1
        return 0

    if not accept:
        return []

    result = []
    for media_range in accept.split(","):
        parts = media_range.split(";")
        media_type = parts.pop(0).strip()
        media_params = []
        q = 1.0
        for part in parts:
            (key, value) = part.lstrip().split("=", 1)
            if key == "q":
                q = float(value)
            else:
                media_params.append((key, value))
        result.append((media_type, tuple(media_params), q))
    result.sort(comparator)
    return result


# removing the dependency on django's encoding util
# for now this is pretty much just ripped straight from django
# removing any django specific elements
class DiabloUnicodeDecodeError(UnicodeDecodeError):
    def __init__(self, obj, *args):
        self.obj = obj
        UnicodeDecodeError.__init__(self, *args)

    def __str__(self):
        original = UnicodeDecodeError.__str__(self)
        return '%s. You passed in %r (%s)' % (original, self.obj,
                type(self.obj))


# removing the dependency on django's encoding util
# for now this is pretty much just ripped straight from django
# removing any django specific elements
def is_protected_type(obj):
    """Determine if the object instance is of a protected type.

    Objects of protected types are preserved as-is when passed to
    force_unicode(strings_only=True).
    """
    return isinstance(obj, (
        types.NoneType,
        int, long,
        datetime.datetime, datetime.date, datetime.time,
        float, Decimal)
    )

# removing the dependency on django's encoding util
# for now this is pretty much just ripped straight from django
# removing any django specific elements
def force_unicode(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Similar to smart_unicode, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and is_protected_type(s):
        return s
    try:
        if not isinstance(s, basestring,):
            if hasattr(s, '__unicode__'):
                s = unicode(s)
            else:
                try:
                    s = unicode(str(s), encoding, errors)
                except UnicodeEncodeError:
                    if not isinstance(s, Exception):
                        raise
                    # If we get to here, the caller has passed in an Exception
                    # subclass populated with non-ASCII data without special
                    # handling to display as a string. We need to handle this
                    # without raising a further exception. We do an
                    # approximation to what the Exception's standard str()
                    # output should be.
                    s = ' '.join([force_unicode(arg, encoding, strings_only,
                            errors) for arg in s])
        elif not isinstance(s, unicode):
            # Note: We use .decode() here, instead of unicode(s, encoding,
            # errors), so that if s is a SafeString, it ends up being a
            # SafeUnicode at the end.
            s = s.decode(encoding, errors)
    except UnicodeDecodeError, e:
        if not isinstance(s, Exception):
            raise DiabloUnicodeDecodeError(s, *e.args)
        else:
            # If we get to here, the caller has passed in an Exception
            # subclass populated with non-ASCII bytestring data without a
            # working unicode method. Try to handle this without raising a
            # further exception by individually forcing the exception args
            # to unicode.
            s = ' '.join([force_unicode(arg, encoding, strings_only,
                    errors) for arg in s])
    return s

# removing the dependency on django's encoding util
# for now this is pretty much just ripped straight from django
# removing any django specific elements
def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and isinstance(s, (types.NoneType, int)):
        return s
    if not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return ' '.join([smart_str(arg, encoding, strings_only,
                        errors) for arg in s])
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s




## ripped out from django to remove the dependence ##
"""
Utilities for XML generation/parsing.
"""

class SimplerXMLGenerator(XMLGenerator):
    def addQuickElement(self, name, contents=None, attrs=None):
        "Convenience method for adding an element with no children"
        if attrs is None: attrs = {}
        self.startElement(name, attrs)
        if contents is not None:
            self.characters(contents)
        self.endElement(name)


#
# util.py ends here
