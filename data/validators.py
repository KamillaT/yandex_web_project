from wtforms.validators import StopValidation


class CheckStringFieldByDigit(object):
    field_flags = ('digit_check',)

    @staticmethod
    def check_string_by_digits_and_symbols(string):
        string = str(string).strip()
        if not string:
            return False
        elif string.count('.') >= 1 or string.count(',') >= 1:
            return False
        elif not string.isdigit():
            return False
        return True

    def __call__(self, form, field):
        if not self.check_string_by_digits_and_symbols(field.data):
            message = field.gettext('Вы ввели неправильное значение')
            field.errors[:] = []
            raise StopValidation(message)
