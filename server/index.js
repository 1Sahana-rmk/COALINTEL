require("dotenv").config();

const express = require("express");
const cors = require("cors");
const multer = require("multer");
const fs = require("fs");
const pool = require("./db");

const app = express();

app.use(cors());
app.use(express.json());

// ------------------------------------
// File Upload Setup
// ------------------------------------

const upload = multer({
    dest: "uploads/"
});

// ------------------------------------
// Health Check
// ------------------------------------

app.get("/api/health", (req, res) => {
    res.json({
        status: "ok",
        message: "COALINTEL backend is running"
    });
});

// ------------------------------------
// Database Test
// ------------------------------------

app.get("/api/db-test", async (req, res) => {
    try {
        const result = await pool.query("SELECT NOW()");

        res.json({
            status: "ok",
            message: "COALINTEL database connected",
            time: result.rows[0].now
        });

    } catch (error) {
        console.error("Database error:", error);

        res.status(500).json({
            status: "error",
            message: "Database connection failed"
        });
    }
});

// ------------------------------------
// Get All Documents
// ------------------------------------

app.get("/api/documents", async (req, res) => {
    try {
        const result = await pool.query(
            "SELECT * FROM documents ORDER BY uploaded_at DESC"
        );

        res.json(result.rows);

    } catch (error) {
        console.error("Documents error:", error);

        res.status(500).json({
            status: "error",
            message: "Failed to fetch documents"
        });
    }
});

// ------------------------------------
// Add Document Metadata
// ------------------------------------

app.post("/api/documents", async (req, res) => {
    try {
        const {
            document_name,
            source_organization,
            reporting_period,
            document_type
        } = req.body;

        const result = await pool.query(
            `INSERT INTO documents
            (document_name, source_organization, reporting_period, document_type)
            VALUES ($1, $2, $3, $4)
            RETURNING *`,
            [
                document_name,
                source_organization,
                reporting_period,
                document_type
            ]
        );

        res.status(201).json({
            status: "ok",
            message: "Document added successfully",
            document: result.rows[0]
        });

    } catch (error) {
        console.error("Insert document error:", error);

        res.status(500).json({
            status: "error",
            message: "Failed to add document"
        });
    }
});

// ------------------------------------
// Upload PDF + Extract Pages
// ------------------------------------

app.post(
    "/api/documents/upload",
    upload.single("pdf"),
    async (req, res) => {

        let filePath = null;

        try {

            // Check whether a file was uploaded
            if (!req.file) {
                return res.status(400).json({
                    status: "error",
                    message: "No PDF file uploaded"
                });
            }

            filePath = req.file.path;

            // ------------------------------------
            // Read uploaded PDF
            // ------------------------------------

            const dataBuffer = fs.readFileSync(filePath);

            // ------------------------------------
            // Load PDF.js
            // ------------------------------------

            const pdfjsLib = await import(
                "pdfjs-dist/legacy/build/pdf.mjs"
            );

            // ------------------------------------
            // Load PDF document
            // ------------------------------------

            const pdfDocument = await pdfjsLib.getDocument({
                data: new Uint8Array(dataBuffer)
            }).promise;

            const totalPages = pdfDocument.numPages;

            console.log(`PDF loaded successfully: ${totalPages} pages`);

            // ------------------------------------
            // Create document record
            // ------------------------------------

            const documentResult = await pool.query(
                `INSERT INTO documents
                (document_name, source_organization, reporting_period, document_type)
                VALUES ($1, $2, $3, $4)
                RETURNING document_id`,
                [
                    req.file.originalname,
                    "Ministry of Coal",
                    "March 2025",
                    "Monthly Statistical Report"
                ]
            );

            const documentId = documentResult.rows[0].document_id;

            console.log(`Document created with ID: ${documentId}`);

            // ------------------------------------
            // Extract each page separately
            // ------------------------------------

            for (
                let pageNumber = 1;
                pageNumber <= totalPages;
                pageNumber++
            ) {

                console.log(
                    `Extracting page ${pageNumber}/${totalPages}`
                );

                const page = await pdfDocument.getPage(pageNumber);

                const textContent = await page.getTextContent();

                const pageText = textContent.items
                    .map(item => item.str)
                    .join(" ");

                // ------------------------------------
                // Store page in database
                // ------------------------------------

                await pool.query(
                    `INSERT INTO document_pages
                    (document_id, page_number, extracted_text)
                    VALUES ($1, $2, $3)`,
                    [
                        documentId,
                        pageNumber,
                        pageText
                    ]
                );
            }

            console.log(
                `Successfully stored ${totalPages} pages`
            );

            // ------------------------------------
            // Delete temporary uploaded file
            // ------------------------------------

            fs.unlinkSync(filePath);
            filePath = null;

            // ------------------------------------
            // Send success response
            // ------------------------------------

            res.status(201).json({
                status: "ok",
                message: "PDF uploaded and pages extracted",
                document_id: documentId,
                pages_detected: totalPages
            });

        } catch (error) {

            console.error(
                "PDF processing error:",
                error
            );

            // Delete temporary file if something failed
            if (filePath && fs.existsSync(filePath)) {
                fs.unlinkSync(filePath);
            }

            res.status(500).json({
                status: "error",
                message: error.message
            });
        }
    }
);

// ------------------------------------
// Start Server
// ------------------------------------

const PORT = 5000;

app.listen(PORT, () => {
    console.log(
        `COALINTEL server running on http://localhost:${PORT}`
    );
});