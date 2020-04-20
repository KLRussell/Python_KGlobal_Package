from KGlobal import Toolbox, master_salt_filepath

import sys

if getattr(sys, 'frozen', False):
    application_path = sys.executable
else:
    application_path = __file__


class Meat(object):
    __meat = None

    def __init__(self, meat=None):
        if not isinstance(meat, (str, type(None))):
            raise ValueError("'meat' %r is not a String" % meat)

        self.meat = meat

    @property
    def meat(self):
        return self.__meat

    @meat.setter
    def meat(self, meat):
        self.__meat = meat

    def __eat_meat(self):
        if self.meat:
            print('I am eating %s' % self.meat)

    __del__ = __eat_meat


class Veggie(object):
    __veggie = None

    def __init__(self, veggie=None):
        if not isinstance(veggie, (str, type(None))):
            raise ValueError("'veggie' %r is not a String" % veggie)

        self.veggie = veggie

    @property
    def veggie(self):
        return self.__veggie

    @veggie.setter
    def veggie(self, veggie):
        self.__veggie = veggie

    def __eat_veggie(self):
        if self.veggie:
            print('I am eating a healthy %s' % self.veggie)

    __del__ = __eat_veggie


class FoodManager(Meat, Veggie):
    def __init__(self, meat=None, veggie=None):
        if not meat and not veggie:
            raise ValueError("'veggie' and 'meat' is None. Please specify something to eat")

        Meat.__init__(self, meat)
        Veggie.__init__(self, veggie)

    def cook_food(self, fire_source):
        if self.meat:
            print('I am cooking {0} with {1} as a heat source'.format(self.meat, fire_source))
        if self.veggie:
            print('I am cooking {0} with {1} as a heat source'.format(self.veggie, fire_source))

    def store_food(self, container):
        if self.meat:
            print('I am storing {0} in {1} as a container'.format(self.meat, container))
        if self.veggie:
            print('I am storing {0} in {1} as a container'.format(self.veggie, container))

    def __del__(self):
        Meat.__del__(self)
        Veggie.__del__(self)


if __name__ == '__main__':
    print(master_salt_filepath())
    changed = False
    tool = Toolbox(application_path)
    mc = tool.main_config
    lc = tool.local_config

    if lc is not None:
        if 'user_name' not in lc.keys():
            lc.setcrypt(key='user_name', val='kdawg')
            changed = True

        if 'user_pass' not in lc.keys():
            lc.setcrypt(key='user_pass', val='test', private=True)
            changed = True

        if 'Fruit' not in lc.keys():
            lc['Fruit'] = ['Apples', 'Oranges', 'Pears']
            changed = True

        if 'Food' not in lc.keys():
            lc['Food'] = FoodManager(meat='Steak', veggie='Spinach')
            changed = True

        if changed:
            lc.sync()

        print(mc)
        print(lc)
        print(lc['user_name'])
        print(lc['user_pass'])
        print(lc['user_name'].peak())
        print(lc['user_pass'].peak())
        print(lc['user_name'].decrypt())
        print(lc['user_pass'].decrypt())
        print(lc['Fruit'])
        lc['Food'].cook_food('Fire')

        if 'Food' in lc.keys():
            del lc['Food']
            lc.sync()
