class Aggregator:

    def compute_tai(self, tpe_data, tr_data):
        """
        TAI = 100 - TPE - TR
        """

        result = []

        for tpe, tr in zip(tpe_data, tr_data):

            value = 100 - (tpe["value"] + tr["value"])

            result.append({
                "cueanexo": tpe["cueanexo"],
                "grado": tpe.get("grado"),
                "value": round(value, 2)
            })

        return result