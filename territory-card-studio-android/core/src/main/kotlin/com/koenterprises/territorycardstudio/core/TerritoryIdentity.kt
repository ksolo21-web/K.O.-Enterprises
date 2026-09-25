package com.koenterprises.territorycardstudio.core

enum class TerritoryClass(val token: String) {
    Residential(""), Apartment("A"), Telephone("T"), TelephoneApartment("TA");
    companion object {
        fun fromToken(token: String): TerritoryClass = when (token) {
            "" -> Residential
            "A" -> Apartment
            "T" -> Telephone
            "TA" -> TelephoneApartment
            else -> throw IllegalArgumentException("Unsupported territory class: $token")
        }
    }
}

data class TerritoryIdentity(
    val baseNumber: Int,
    val territoryClass: TerritoryClass = TerritoryClass.Residential,
    val suffix: Char? = null
) {
    init {
        require(baseNumber > 0) { "Territory base number must be positive" }
        require(suffix == null || suffix in 'a'..'z') { "Suffix must be lowercase a-z" }
    }
    val displayId: String get() = buildString {
        append(territoryClass.token)
        append(baseNumber)
        suffix?.let(::append)
    }
    val canonicalFilename: String get() = buildString {
        append("Territory - ")
        append(baseNumber.toString().padStart(3, '0'))
        append(territoryClass.token)
        suffix?.let(::append)
        append(".pdf")
    }
    companion object {
        private val visibleId = Regex("^(TA|A|T)?([1-9][0-9]*)([a-z])?$")
        fun parse(displayId: String): TerritoryIdentity {
            val match = visibleId.matchEntire(displayId)
                ?: throw IllegalArgumentException("Invalid visible territory ID: $displayId")
            val result = TerritoryIdentity(
                baseNumber = match.groupValues[2].toInt(),
                territoryClass = TerritoryClass.fromToken(match.groupValues[1]),
                suffix = match.groupValues[3].singleOrNull()
            )
            require(result.displayId == displayId) { "Visible territory ID is not canonical: $displayId" }
            return result
        }
    }
}
