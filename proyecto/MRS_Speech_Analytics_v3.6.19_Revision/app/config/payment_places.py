"""Catálogo operativo compartido; conservar convenios y variantes autorizadas."""
AUTHORIZED_PAYMENT_PLACES = {
    "TIENDA DE ORIGEN": ["en tienda", "en la tienda", "en su tienda", "en la misma tienda", "su misma tienda"],
    "FARMACIAS DEL AHORRO": ["farmacias del ahorro", "farmacia del ahorro", "farmacias de la oro", "farmacia de la oro", "farmacias de la ahorro", "farmacia de la ahorro", "farmacia de la horro", "farmacias de la horro", "farmacia de la orro", "farmacias de la orro", "formacia de la oro", "formacias de la oro"],
    "7-ELEVEN": ["7 eleven", "seven eleven", "7-11", "7/11", "7 y 11", "seven y leven", "7 11", "salvenileven", "sevenileven"],
    "CHEDRAUI": ["chedraui", "che dragui", "chedragui", "che draui", "chedrawi", "chedrague", "chedraguy"],
    "WOOLWORTH": ["woolworth", "bulbor", "bulbo", "bulvor", "hulbor", "hulvor", "ulbor", "wulbor", "wulvor", "wulworth", "bulboard"],
    "TIENDAS DEL SOL": ["tiendas del sol", "tienda del sol", "del sol"],
    "CIRCLE K": ["circle k", "circulo k", "circulo que", "circulquei", "circuloquei", "circuluka", "circulcay"],
    "KIOSKO": ["kiosko", "kiosco", "kiosk", "kyosko", "quiosco", "quiosko", "qiosco"],
    "TIENDAS NETO": ["tiendas neto", "tienda neto", "neto"],
    "ABARREY": ["abarrey", "abarray"],
    "7/24 MIX": ["7 24 mix", "7/24 mix", "724 mix"],
    "FARMACIAS YZA": ["farmacias yza", "farmacia yza", "farmacias isa", "farmacia isa"],
    "FARMACIAS ROMA": ["farmacias roma", "farmacia roma"],
    "TIENDAS 3B": ["tiendas 3b", "tienda 3b", "tiendas tres b", "tienda tres b"],
    "TIENDAS SIX": ["tiendas six", "tienda six", "tiendas 6", "tienda 6"],
    # IMPORTANTE: mencionar solamente el banco NO acredita un lugar de pago
    # autorizado. Para bancos se exige el convenio/servicio correcto.
    "SANTANDER": ["convenio 3411", "convenio numero 3411", "convenio número 3411"],
    "BBVA": ["convenio 1042378", "convenio numero 1042378", "convenio número 1042378"],
    "BANAMEX": ["pago de servicio 4626", "servicio 4626", "convenio 4626"],
    # Tiendas de origen autorizadas (regla operativa MRS/Bradescard)
    "C&A": ["c&a", "c y a", "cy a", "ce y a"],
    "CUIDADO CON EL PERRO": ["cuidado con el perro"],
    "MALAYERBA": ["malayerba", "mala yerba"],
    "BODEGA AURRERA": ["bodega aurrera"],
    "MI BODEGA AURRERA": ["mi bodega aurrera"],
    "BODEGA AURRERA EXPRESS": ["bodega aurrera express", "bodega express"],
    "PROMODA": ["promoda"],
    "SUBURBIA": ["suburbia"],
}
