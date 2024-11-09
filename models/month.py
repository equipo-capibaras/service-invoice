from enum import StrEnum


class Month(StrEnum):
    JANUARY = 'January'
    FEBRUARY = 'February'
    MARCH = 'March'
    APRIL = 'April'
    MAY = 'May'
    JUNE = 'June'
    JULY = 'July'
    AUGUST = 'August'
    SEPTEMBER = 'September'
    OCTOBER = 'October'
    NOVEMBER = 'November'
    DECEMBER = 'December'

    def to_int(self) -> int:
        """Convierte el Enum a su número de mes correspondiente."""
        return list(Month).index(self) + 1

    @staticmethod
    def from_int(month_number: int) -> "Month":
        """Devuelve el Enum correspondiente al número de mes."""
        if not (1 <= month_number <= 12):
            raise ValueError("El número del mes debe estar entre 1 y 12.")
        
        months = list(Month)
        return Month(months[month_number - 1])  