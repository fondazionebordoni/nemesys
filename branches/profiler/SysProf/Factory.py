
from NemesysException import FactoryException

def class_forname(name): 
    try:  
        parts = name.split('.')
        module = ".".join(parts[:-1])
        m = __import__( module )
        for comp in parts[1:]:
            m = getattr(m, comp)  
    except ImportError as e:
        raise FactoryException(e)
    except AttributeError as e:
        raise FactoryException(e)
    except ValueError as e:
        raise FactoryException(e)       
    return m()

