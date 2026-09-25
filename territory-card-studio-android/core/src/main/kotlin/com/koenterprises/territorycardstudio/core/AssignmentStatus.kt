package com.koenterprises.territorycardstudio.core

import java.io.Reader

data class AssignmentStatus(
    val displayId: String,
    val status: String,
    val roadAssignmentStatus: String,
    val buildingAssignmentStatus: String,
    val needsNewCard: Boolean,
    val canonicalFilename: String,
    val referenceFile: String
) {
    val identity: TerritoryIdentity = TerritoryIdentity.parse(displayId)
    init {
        require(identity.canonicalFilename == canonicalFilename) { "Canonical filename mismatch" }
        if (needsNewCard) require(status == "needs_new_card") { "needs_new_card status required" }
    }
}

class AssignmentStatusIndex private constructor(val records: List<AssignmentStatus>) {
    private val byDisplayId = records.associateBy { it.displayId }
    fun get(displayId: String): AssignmentStatus? = byDisplayId[displayId]
    val needsNewCard: List<AssignmentStatus> get() = records.filter { it.needsNewCard }
    companion object {
        fun load(reader: Reader): AssignmentStatusIndex {
            val rows = Csv4180.parse(reader)
            require(rows.isNotEmpty()) { "Assignment CSV is empty" }
            val expected = listOf("display_id", "status", "road_assignment_status", "building_assignment_status", "needs_new_card", "canonical_filename", "reference_file")
            require(rows.first() == expected) { "Assignment CSV schema drift" }
            val records = rows.drop(1).filter { row -> row.any { it.isNotEmpty() } }.map { row ->
                require(row.size == expected.size) { "Assignment CSV field count mismatch" }
                AssignmentStatus(row[0], row[1], row[2], row[3], when (row[4]) { "True" -> true; "False" -> false; else -> error("Invalid boolean") }, row[5], row[6])
            }
            require(records.map { it.displayId }.distinct().size == records.size) { "Duplicate display IDs" }
            return AssignmentStatusIndex(records)
        }
    }
}

private object Csv4180 {
    fun parse(reader: Reader): List<List<String>> {
        val text = reader.readText()
        val rows = mutableListOf<MutableList<String>>()
        var row = mutableListOf<String>()
        val field = StringBuilder()
        var quoted = false
        var i = 0
        fun endField() { row.add(field.toString()); field.setLength(0) }
        fun endRow() { endField(); rows.add(row); row = mutableListOf() }
        while (i < text.length) {
            val c = text[i]
            if (quoted) {
                when {
                    c == '"' && i + 1 < text.length && text[i + 1] == '"' -> { field.append('"'); i++ }
                    c == '"' -> quoted = false
                    else -> field.append(c)
                }
            } else {
                when (c) {
                    '"' -> { require(field.isEmpty()) { "Unexpected quote" }; quoted = true }
                    ',' -> endField()
                    '\n' -> endRow()
                    '\r' -> { if (i + 1 < text.length && text[i + 1] == '\n') i++; endRow() }
                    else -> field.append(c)
                }
            }
            i++
        }
        require(!quoted) { "Unclosed quote" }
        if (field.isNotEmpty() || row.isNotEmpty()) endRow()
        return rows
    }
}
