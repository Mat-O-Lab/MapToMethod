# MapToMethod

[![Publish Docker image](https://github.com/Mat-O-Lab/MapToMethod/actions/workflows/PublishContainer.yml/badge.svg)](https://github.com/Mat-O-Lab/MapToMethod/actions/workflows/PublishContainer.yml)
[![Test Examples](https://github.com/Mat-O-Lab/MapToMethod/actions/workflows/TestExamples.yml/badge.svg?branch=main&event=push)](https://github.com/Mat-O-Lab/MapToMethod/actions/workflows/TestExamples.yml)

**Create semantic mapping rules for your data - no RML expertise required.**

🌐 **Demo:** http://maptomethod.matolab.org

---

## Why MapToMethod?

MapToMethod simplifies the creation of YARRRML mapping rules that link your data to semantic knowledge graphs. Whether you're working with materials science experiments, research datasets, or any JSON-LD data, MapToMethod provides an interactive interface to create conditional mapping rules without needing to understand RML syntax.

### Key Benefits

- ✅ **Interactive Web UI** - Visual form-based mapping creation
- ✅ **REST API** - Programmatic access for automation workflows
- ✅ **Conditional Mappings** - Create rules that only apply when conditions match
- ✅ **Template-Based** - Reference semantic templates from knowledge graphs
- ✅ **YARRRML Output** - Human-readable mapping rules
- ✅ **Production-Ready** - Docker deployment, CI/CD tested

### How MapToMethod Fits Your Workflow

MapToMethod works together with [RDFConverter](https://github.com/Mat-O-Lab/RDFConverter) to provide a complete semantic data transformation pipeline:

1. **MapToMethod** - CREATE mapping rules (YARRRML) interactively
2. **RDFConverter** - EXECUTE those rules to generate RDF

**Example Workflow:**
```
JSON-LD Data → MapToMethod → YARRRML Mapping Rules → RDFConverter → Semantic RDF
```

You can also test your mappings manually with [YARRRML Matey](https://rml.io/yarrrml/matey/) online editor.

---

## Quick Start

### Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose installed and running
- Port 5005 available (or configure a different port)

### 5-Minute Setup

```bash
# 1. Clone the repository
git clone https://github.com/Mat-O-Lab/MapToMethod
cd MapToMethod

# 2. Start the service
docker compose up -d

# 3. Access the application
# Web UI: http://localhost:5005
# API docs: http://localhost:5005/api/docs
```

### Your First Mapping

1. **Open the Web UI** at http://localhost:5005
2. **Enter your data URL** - Use the example or your own JSON-LD file
3. **Select or enter a method URL** - The semantic template to map against
4. **Click "Start Mapping"** - MapToMethod will query entities from both sources
5. **Match entities** - Use dropdown selectors to map data fields to template concepts
6. **Generate YARRRML** - Click "Create Mapping" to get your mapping file

**Test your mapping** with [YARRRML Matey](https://rml.io/yarrrml/matey/):
- Paste your JSON-LD data in the left panel
- Paste the generated YARRRML in the "Input: YARRRML" section
- Update source URLs to `data.json` to point at your data
- Click "Generate LD" to see the semantic RDF output

![Matey Example](./screenshots/matey.png)

---

## How It Works

MapToMethod follows a simple 3-step process:

```
┌─────────────────────────────────────┐
│  1. Query Entities                  │
│  - Load data metadata (JSON-LD)     │
│  - Load method template (RDF)       │
│  - Extract mappable entities        │
└─────────────────┬───────────────────┘
                  ↓
┌─────────────────────────────────────┐
│  2. Create Mappings                 │
│  - User matches data to template    │
│  - Define conditional rules         │
│  - Configure advanced options       │
└─────────────────┬───────────────────┘
                  ↓
┌─────────────────────────────────────┐
│  3. Generate YARRRML                │
│  - Output human-readable rules      │
│  - Ready for RDFConverter           │
│  - Compatible with RML tools        │
└─────────────────────────────────────┘
```

---

## Real-World Use Case: Materials Testing Laboratory

### The Challenge

A materials testing laboratory conducts tensile tests according to DIN EN ISO 527-3 standard. Each test generates:
- CSV data with force and displacement measurements
- Metadata about specimen dimensions, test parameters
- Information needs to be FAIR (Findable, Accessible, Interoperable, Reusable)

**Problem:** Raw CSV and metadata aren't semantically structured. Other researchers can't easily understand or reuse the data.

### The Solution with MapToMethod

#### Step 1: Prepare Semantic Data

Use [CSVToCSVW](https://github.com/Mat-O-Lab/CSVToCSVW) to convert CSV to CSVW metadata (JSON-LD):
- Columns become `csvw:Column` entities with names and datatypes
- Annotations capture specimen info and test parameters
- Result: Semantic data description

#### Step 2: Create Mapping with MapToMethod

1. **Load data metadata:** Point to the CSVW JSON-LD file
2. **Load method template:** Reference DIN EN ISO 527-3 semantic template
3. **Map entities:**
   - "Standardkraft" column → `ForceMeasurement` in template
   - "Standardweg" column → `LengthMeasurement` in template
   - "aktuelle Probe" annotation → `SpecimenID` in template
   - "Probenbreite b0" → `WidthMeasurement`
   - "Prüfgeschwindigkeit" → `CrossheadSpeedSetPointValue`

4. **Generate YARRRML:** MapToMethod creates conditional mapping rules

#### Step 3: Execute Mapping with RDFConverter

Use [RDFConverter](https://github.com/Mat-O-Lab/RDFConverter) to apply the YARRRML rules:
- Transforms CSVW metadata + CSV data into semantic RDF
- Links measurements to standardized method concepts
- Generates knowledge graph conforming to DIN standard

### The Result

**Before:**
- Isolated CSV files with cryptic column names
- Metadata only interpretable by domain experts
- No machine-readable structure

**After:**
- Fully semantic knowledge graph
- Measurements linked to ISO standard concepts
- Data is FAIR and interoperable
- Template reusable for all future tensile tests
- Other labs using same standard can understand data

### Example Output

The generated YARRRML creates conditional rules like:

```yaml
mappings:
  ForceMeasurement:
    sources: [columns]
    s: $(@id)
    condition:
      function: equal
      parameters:
      - [str1, $(name)]
      - [str2, "Standardkraft"]
    po:
    - ['http://purl.obolibrary.org/obo/RO_0010002', 'template:ForceMeasurement~iri']
```

This rule says: "When you find a column named 'Standardkraft', link it to the ForceMeasurement entity in the template."

### Benefits

✅ **Reusability** - Same template works for all DIN EN ISO 527-3 tests
✅ **Standardization** - Data conforms to international standards
✅ **Interoperability** - Other labs can understand and reuse data
✅ **Automation** - Once created, mappings can be applied to all future tests
✅ **FAIR Data** - Meets all FAIR principles for scientific data

---

## API Reference

MapToMethod provides a REST API for programmatic access. Full interactive documentation is available at `/api/docs` when the service is running.

### Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/entities` | POST | Query entities from a semantic graph |
| `/api/mapping` | POST | Generate YARRRML mapping file |
| `/api/docs` | GET | Interactive API documentation (Swagger UI) |

### Query Entities Endpoint

**Purpose:** Extract mappable entities from JSON-LD data or RDF graphs.

```bash
curl -X POST "http://localhost:5005/api/entities" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/data.json",
    "entity_classes": [
      "http://www.w3.org/ns/csvw#Column",
      "http://www.w3.org/ns/oa#Annotation"
    ]
  }'
```

**Response:**
```json
{
  "entities": {
    "column1": {
      "uri": "http://example.com/column1",
      "property": "name",
      "text": "Force"
    }
  },
  "base_namespace": "http://example.com/"
}
```

### Generate Mapping Endpoint

**Purpose:** Create YARRRML mapping rules based on entity pairs.

```bash
curl -X POST "http://localhost:5005/api/mapping" \
  -H "Content-Type: application/json" \
  -d '{
    "data_url": "https://example.com/data.json",
    "method_url": "https://example.com/template.ttl",
    "use_template_rowwise": false,
    "map": {
      "TemplateEntity1": "data-entity-1",
      "TemplateEntity2": "data-entity-2"
    }
  }'
```

**Response:** YARRRML file (application/x-yaml)

### Python Integration Example

```python
import requests

# Query entities from your data
response = requests.post(
    "http://localhost:5005/api/entities",
    json={
        "url": "https://example.com/data.json",
        "entity_classes": [
            "http://www.w3.org/ns/csvw#Column"
        ]
    }
)
entities = response.json()

# Generate mapping
mapping_response = requests.post(
    "http://localhost:5005/api/mapping",
    json={
        "data_url": "https://example.com/data.json",
        "method_url": "https://example.com/template.ttl",
        "map": {
            "ForceColumn": "force-measurement"
        }
    }
)

# Save YARRRML file
with open("mapping.yaml", "wb") as f:
    f.write(mapping_response.content)
```

---

## Advanced Features

### Template Duplication for Table Data

**Use Case:** When your data contains multiple rows representing different experiments, you can duplicate the method template for each row.

**Feature:** "Duplicate Template for Table Data" checkbox (or `use_template_rowwise` parameter)

**How it works:**
- ☑️ **Checked (true):** Creates separate template instances for each data row
- ☐️ **Unchecked (false):** Shares one template instance across all data

**Example Scenario:**

You have CSV data with 100 rows of tensile test results. Each row is a different specimen test.

- **Without duplication:** All 100 measurements map to the same template entities (data gets merged)
- **With duplication:** Each row gets its own copy of the template (100 independent experiment descriptions)

**API Usage:**
```json
{
  "use_template_rowwise": true
}
```

### Advanced Settings - Entity Query Configuration

The advanced settings control **which entities** are queried from your data and template graphs using SPARQL class hierarchy queries.

#### Data Subject Super Classes

**Purpose:** Define which entity types to query **from your data** as mapping sources.

**Default values:**
- `http://www.w3.org/ns/oa#Annotation` - Annotation entities
- `http://www.w3.org/ns/csvw#Column` - CSV column descriptions

**How it works:**
1. MapToMethod queries the data graph for all instances of these classes
2. Also includes all subclasses (using `rdfs:subClassOf*` reasoning)
3. These become the dropdown options in the Web UI

**Example:** If your data uses custom annotation types that extend `oa:Annotation`, they'll automatically be discovered.

**API Parameter:** `data_super_classes`

#### Method Object Super Classes

**Purpose:** Define which entity types to query **from the template** as mapping targets.

**Default values:**
- `https://spec.industrialontologies.org/ontology/core/Core/InformationContentEntity`
- `http://purl.obolibrary.org/obo/BFO_0000008` (TemporalRegion)

**How it works:**
1. MapToMethod queries the template graph for all instances of these classes
2. These become the mapping target fields in the Web UI
3. Each matched entity creates a YARRRML mapping rule

**Example:** If your method template uses domain-specific measurement types that extend ICE, they'll be found.

**API Parameter:** `method_super_classes`

#### Mapping Predicate

**Purpose:** The RDF property used to link data entities to template entities in the generated mapping.

**Default value:** `http://purl.obolibrary.org/obo/RO_0010002` (content-to-bearing relation)

**Usage:** This appears in the YARRRML output as the predicate connecting your data to the template.

**API Parameter:** `predicate`

### Full Advanced Configuration Example

```json
{
  "data_url": "https://example.com/data.json",
  "method_url": "https://example.com/template.ttl",
  "use_template_rowwise": true,
  "data_super_classes": [
    "http://www.w3.org/ns/csvw#Column",
    "http://www.w3.org/ns/oa#Annotation"
  ],
  "predicate": "http://purl.obolibrary.org/obo/RO_0010002",
  "method_super_classes": [
    "https://spec.industrialontologies.org/ontology/core/Core/InformationContentEntity",
    "http://purl.obolibrary.org/obo/BFO_0000008"
  ],
  "map": {
    "TemplateEntity": "data-entity"
  }
}
```

---

## Deployment

### Development Mode

For local development with hot-reloading:

```bash
# Using compose.dev.yml
docker compose -f compose.dev.yml up

# Or set environment variable
APP_MODE=development
```

Access at: http://localhost:5005

### Production Mode

For production deployment:

```bash
docker compose up -d
```

Or pull the pre-built container:

```bash
docker pull ghcr.io/mat-o-lab/maptomethod:latest
docker run -p 5005:5000 ghcr.io/mat-o-lab/maptomethod:latest
```

### Environment Variables

Configure via `.env` file or environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_MODE` | "development" or "production" | development |
| `PORT` | Internal container port | 5000 |
| `APP_NAME` | Application name | MaptoMethod |
| `APP_VERSION` | Version string | v1.1.2 |
| `SERVER_URL` | Public server URL | https://maptomethod.matolab.org |
| `SSL_VERIFY` | Verify SSL certificates | True |

---

## Troubleshooting

### Common Issues

**Docker not running**
```
Error: Cannot connect to the Docker daemon
```
→ Start Docker Desktop/Service and try again

**Port already in use**
```
Error: bind: address already in use
```
→ Change the port in `compose.yml` or stop conflicting services:
```bash
# Find what's using port 5005
lsof -i :5005
# Or use a different port
PORT=5006 docker compose up
```

**No entities found**
```
"entities": {}
```
→ Check:
- Data URL is accessible
- Entity classes match your data's RDF types
- Data is valid JSON-LD or RDF
- Try with default classes first

**YARRRML generates but no mappings match**

→ Verify:
- The `property` field in entities (name, label, etc.) exists in your data
- The condition strings match exactly (case-sensitive)
- Data structure supports the iterator (e.g., `$..columns[*]` needs a columns array)

**Template URL returns 404**

→ Ensure:
- The method template URL is publicly accessible
- The URL points to a valid RDF file (Turtle, RDF/XML, N3, JSON-LD)
- No authentication is required (or provide credentials)

### Debug Mode

Enable detailed logging:

```bash
# Set in .env or environment
APP_MODE=development

# Restart services
docker compose restart
```

View logs in real-time:
```bash
docker compose logs -f
```

### Check Service Health

```bash
# Check if service is running
curl http://localhost:5005/info

# Should return version and configuration
```

---

## FAQ

**Q: What's the difference between MapToMethod and RDFConverter?**

A: They're complementary tools:
- **MapToMethod** helps you CREATE YARRRML mapping rules interactively
- **RDFConverter** EXECUTES those rules to transform data into RDF
- Use MapToMethod first to define mappings, then RDFConverter to apply them

**Q: Can I use the generated YARRRML with other tools?**

A: Yes! The output is standard YARRRML format compatible with:
- [RDFConverter](https://github.com/Mat-O-Lab/RDFConverter) - Transform data to RDF
- [YARRRML Matey](https://rml.io/yarrrml/matey/) - Online editor and tester
- [RML Mapper](https://github.com/RMLio/rmlmapper-java) - Direct RML execution
- Any tool that supports YARRRML/RML specifications

**Q: What data formats are supported?**

A: Input data must be:
- **JSON-LD** (preferred)
- **CSVW metadata** (JSON-LD format)
- Any RDF format that can be converted to JSON-LD (Turtle, RDF/XML, etc.)

The key requirement is that data must be semantic (contain RDF types and properties).

**Q: Can I create mappings without a template?**

A: Yes, but templates are recommended. Without a template:
- You can still create mappings between data entities
- The output links data properties to URIs you specify
- Templates provide semantic structure and reusability

**Q: How do I create a custom semantic template?**

A: Create an RDF file (Turtle, RDF/XML, etc.) with:
1. Define your entities as instances of relevant ontology classes
2. Use meaningful URIs for each entity
3. Add rdfs:label or similar properties for human-readable names
4. Host it at a publicly accessible URL or use file:// for local files
5. Reference it in MapToMethod's method URL field

**Q: Does my data leave the server?**

A: MapToMethod fetches URLs you provide but doesn't store or transmit your data elsewhere. All processing happens on the server where you deploy it. For sensitive data, deploy locally or on your own infrastructure.

**Q: Can I automate mapping creation?**

A: Yes! Use the `/api/mapping` endpoint to:
- Integrate mapping generation into CI/CD pipelines
- Batch process multiple datasets
- Programmatically create mappings from Python, R, JavaScript, etc.

See the API Reference section for examples.

**Q: What if my data has nested structures?**

A: MapToMethod automatically handles nested JSON-LD:
- Uses JSONPath iterators (e.g., `$..columns[*]`)
- Discovers arrays within your data structure
- Creates appropriate YARRRML source definitions

**Q: How do I contribute or report issues?**

A:
- **Report bugs:** Open an issue at https://github.com/Mat-O-Lab/MapToMethod/issues
- **Contribute code:** Submit a pull request
- **Questions:** Contact the team via the Mat-O-Lab organization

---

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments
The authors would like to thank the Federal Government and the Heads of Government of the Länder for their funding and support within the framework of the [Platform Material Digital](https://www.materialdigital.de) consortium. Funded by the German [Federal Ministry of Education and Research (BMBF)](https://www.bmbf.de/bmbf/en/) through the [MaterialDigital](https://www.bmbf.de/SharedDocs/Publikationen/de/bmbf/5/31701_MaterialDigital.pdf?__blob=publicationFile&v=5) Call in Project [KupferDigital](https://www.materialdigital.de/project/1) - project id 13XP5119.
