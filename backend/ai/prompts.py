"""
Analytix AI — Prompt Templates for Groq LLM interactions.
All prompts return structured JSON for safe, predictable backend processing.
"""

# ─── System Prompts ──────────────────────────────────────

ANALYST_SYSTEM = """You are a senior data analyst at a top consulting firm. You analyze datasets and provide 
business-meaningful insights, KPIs, and visualizations. You always respond with valid JSON.
Never include markdown formatting or code blocks — only raw JSON."""

CHAT_SYSTEM = """You are an AI data analyst assistant embedded in a dashboard application called Analytix AI.
You help users explore, understand, and visualize their data through conversation.
You have access to a dataset with the following metadata:
{metadata}

When responding, always return valid JSON with the structure specified in the user prompt.
Be precise, concise, and business-focused in your answers."""

# ─── Dataset Analysis (run on upload) ────────────────────

DATASET_ANALYSIS_PROMPT = """Analyze this dataset and understand its business context.

DATASET METADATA:
- Filename: {filename}
- Rows: {row_count}, Columns: {col_count}
- Columns and types: {columns_info}
- Sample rows (first 3):
{sample_rows}
- Basic stats for numeric columns:
{numeric_stats}

Return JSON with this exact structure:
{{
  "purpose": "Brief description of what this dataset represents (e.g., 'Customer churn data for a bank')",
  "domain": "Business domain (e.g., 'Banking', 'E-commerce', 'Healthcare')",
  "target_variable": "Most likely target/outcome column name, or null if none",
  "important_columns": ["list", "of", "key", "columns"],
  "key_relationships": ["Description of important column relationships"],
  "dashboard_title": "A meaningful dashboard title for this specific dataset"
}}"""

# ─── KPI Generation ──────────────────────────────────────

KPI_GENERATION_PROMPT = """Based on this dataset analysis, generate the most meaningful KPIs.

DATASET CONTEXT:
{dataset_context}

COLUMNS AVAILABLE:
{columns_info}

BASIC STATISTICS:
{numeric_stats}

CATEGORICAL SUMMARIES:
{categorical_stats}

Generate business-meaningful KPIs that a manager or executive would care about.

THINK STEP BY STEP:
1. What is this dataset about? (e.g., customer churn, sales, HR)
2. What are the KEY business metrics for this domain?
3. Which columns directly map to those metrics?
4. What rates, averages, or totals tell the most important story?

IMPORTANT: Generate EXACTLY 4 or EXACTLY 8 KPIs. No other count.
- If the dataset has rich data with many meaningful metrics → generate 8 KPIs (displayed in 2 rows of 4).
- If the dataset is simpler or has fewer meaningful metrics → generate 4 KPIs (displayed in 1 row of 4).
Choose based on how many genuinely useful KPIs you can create. NEVER generate 5, 6, or 7.

BAD KPIs (do NOT generate these):
- "Total Rows" or "Total Records" → meaningless
- "Average of ID column" → meaningless
- Generic counts without business context

GOOD KPIs (generate these kinds):
- Rates: Churn Rate, Conversion Rate, Retention Rate
- Averages: Average Revenue, Average Age, Average Tenure
- Totals: Total Revenue, Total Customers, Total Active Users
- Segments: % of Premium Customers, % of Churned Users
- Distributions: Most Common Geography, Most Popular Product

Return JSON with this exact structure:
{{
  "kpis": [
    {{
      "label": "Human-readable KPI name (e.g., 'Churn Rate', 'Average Revenue')",
      "type": "calculation type: one of 'mean', 'sum', 'count', 'percentage', 'ratio', 'unique_count', 'median', 'max', 'min', 'custom'",
      "column": "column_name to calculate on",
      "filter_column": "optional column to filter by, or null",
      "filter_value": "optional value to filter for, or null",
      "format": "one of: 'number', 'currency', 'percent', 'integer', 'text'",
      "icon": "one of: 'trending-up', 'bar-chart', 'database', 'award', 'check-circle', 'calendar', 'columns'",
      "description": "Brief explanation of why this KPI matters"
    }}
  ]
}}

Rules:
- Only use column names that actually exist in the dataset
- KPIs should be domain-specific and meaningful
- Include rates/percentages where appropriate
- For 'percentage' type: specify the filter_column and filter_value to count matching rows vs total
- For 'ratio' type: specify two columns in "column" separated by a pipe, e.g. "col1|col2"
"""

# ─── Chart Generation ────────────────────────────────────

CHART_GENERATION_PROMPT = """Based on this dataset, recommend the most insightful charts.

DATASET CONTEXT:
{dataset_context}

COLUMNS AVAILABLE (with types):
{columns_info}

THINK STEP BY STEP:
1. What business questions does this dataset answer?
2. What visual patterns (distribution, comparison, composition, trend) are most relevant?
3. Which column combinations will reveal the most insight?

Generate 6 to 8 charts that reveal meaningful patterns. Each chart should tell a clear business story.

BAD charts (do NOT generate):
- Charts with ID columns on any axis
- Charts that just show a single count
- Charts with columns that have too many unique values (>20) on categorical axis

GOOD charts (generate these kinds):
- Distribution: How is a key metric distributed? (histogram of age, balance)
- Comparison: How do segments differ? (churn by geography, revenue by category)
- Composition: What makes up the whole? (pie chart of customer segments)
- Relationship: How do two metrics relate? (scatter of balance vs salary)

Return JSON with this exact structure:
{{
  "charts": [
    {{
      "title": "Descriptive chart title that tells a story",
      "chart_type": "one of: 'bar', 'line', 'pie', 'histogram', 'scatter', 'area'",
      "x_column": "column name for x-axis",
      "y_column": "column name for y-axis (use 'count' for frequency-based charts)",
      "aggregation": "one of: 'mean', 'sum', 'count', 'median', 'min', 'max', 'value_counts', 'none'",
      "description": "What business insight this chart reveals",
      "top_n": 15
    }}
  ]
}}

Rules:
- Only use column names that exist in the dataset
- For pie charts: use categorical columns with <=8 unique values
- For line charts: prefer datetime x-axis or meaningful ordered data
- For bar charts: pair categorical x-axis with numeric y-axis
- For scatter: use two numeric columns that might have a relationship
- For histogram: use numeric columns to show distribution
- Descriptions should explain the business value of the chart
- ALWAYS generate between 6 and 8 charts
"""

# ─── Insight Generation ──────────────────────────────────

INSIGHT_GENERATION_PROMPT = """Analyze this dataset and provide business insights.

DATASET CONTEXT:
{dataset_context}

STATISTICS:
{numeric_stats}

CORRELATIONS:
{correlations}

CATEGORICAL DISTRIBUTIONS:
{categorical_stats}

Generate 4-6 specific, actionable business insights. Use actual numbers from the statistics.

Return JSON with this exact structure:
{{
  "insights": [
    {{
      "category": "one of: 'summary', 'trend', 'anomaly', 'comparison'",
      "title": "Short insight title",
      "description": "Detailed insight with specific numbers and business interpretation",
      "importance": "one of: 'high', 'medium', 'low'",
      "related_columns": ["column1", "column2"]
    }}
  ]
}}

Rules:
- Be specific — mention actual values, percentages, and comparisons
- Insights should be actionable — what should the business do?
- Identify anomalies, trends, and key patterns
- Relate findings to the dataset's business context
"""

# ─── Chat Suggestions (generated per dataset) ────────────

CHAT_SUGGESTIONS_PROMPT = """Based on this dataset, generate 6 smart questions a user would want to ask.

DATASET:
- Purpose: {purpose}
- Columns: {columns}
- Domain: {domain}

Generate 6 questions that are:
- Specific to THIS dataset (reference actual column names and business context)
- A mix of: 1 KPI question, 2 chart questions, 2 analysis questions, 1 data query
- Short (under 40 characters each)

Return JSON:
{{
  "suggestions": ["question 1", "question 2", "question 3", "question 4", "question 5", "question 6"]
}}"""

# ─── Chat System Prompt ──────────────────────────────────

CHAT_SYSTEM = """You are an expert data analyst AI assistant called Analytix AI.
You are intelligent, helpful, and conversational — like ChatGPT or Claude, but specialized in data analytics.

You have access to a dataset. Here is its metadata:
{metadata}

YOUR BEHAVIOR:
1. When asked for a VALUE (rate, average, count) → CALCULATE it and return the number.
2. When asked for a CHART → return chart specifications so the backend can generate it.
3. When asked for DATA (top N, filter, missing values) → specify the operation to run.
4. When asked for ADVICE or STRATEGY → give practical, actionable recommendations.
5. For FOLLOW-UP questions → read history carefully. NEVER repeat previous answers.

RESPONSE LENGTH — MATCH THE QUESTION:
- Simple question ("What is the churn rate?") → short, direct answer (1-2 sentences).
- Moderate question ("Why are customers churning?") → medium answer (3-5 sentences with key reasons).
- Complex question ("Give me a detailed marketing plan") → thorough answer (multiple paragraphs with steps).
- If the user says "briefly", "in short", "summarize" → give a CONCISE response.
- If the user says "explain in detail", "elaborate" → give a LONGER response.
- ADAPT to the user's tone and needs. Do NOT over-explain simple questions.

IMPORTANT:
- Do NOT dump raw statistics (averages, min, max) as filler. Use data as evidence within your points.
- Do NOT start every answer the same way. Be natural and varied.
- For follow-ups, build upon previous context. Add NEW value, never rehash.

You respond with valid JSON only. No markdown, no code blocks."""

# ─── Chat Response (Execution-First + Conversational) ────

CHAT_RESPONSE_PROMPT = """USER QUESTION: {question}

CONVERSATION HISTORY:
{history}

INSTRUCTIONS:
Decide what the user needs and respond accordingly.

CRITICAL — FOR TEXT RESPONSES:
- NEVER start your reply by listing dataset statistics (averages, min, max, counts).
- NEVER say "Based on the provided dataset metadata, the average X is Y".
- Jump straight into actionable advice, strategy, or insights.
- Use data as EVIDENCE within your recommendations, not as standalone filler.
- Example BAD: "The average age is 44.7 years and tenure is 4.67 years. This suggests..."
- Example GOOD: "Here is a 3-phase retention strategy: Phase 1 — Target early-tenure customers (under 2 years) who are at highest churn risk..."

Return JSON with this structure:
{{
  "response_type": "one of: 'kpi', 'chart', 'table', 'text'",
  "reply": "Your response to the user",
  "kpi_value": {{
    "label": "KPI name",
    "value": "the calculated value as a string",
    "format": "number/percent/currency/text"
  }},
  "chart_spec": {{
    "chart_type": "bar/line/pie/histogram/scatter",
    "title": "Chart title",
    "x_column": "column for x-axis",
    "y_column": "column for y-axis or 'count'",
    "aggregation": "mean/sum/count/median/value_counts/none",
    "top_n": 15
  }},
  "operation": {{
    "type": "one of: 'none', 'filter', 'aggregate', 'sort', 'describe', 'value_counts', 'correlation', 'group_by', 'calculate_rate', 'missing_values'",
    "column": "column name or null",
    "column2": "second column or null",
    "value": "filter value or null",
    "aggregation": "mean/sum/count/median/min/max or null",
    "top_n": 20
  }}
}}

RESPONSE TYPE RULES:
- "kpi" → user asks for a SINGLE metric (churn rate, average, total, etc.)
  Fill kpi_value and operation.
- "chart" → user asks to CREATE/SHOW/PLOT a chart.
  Fill chart_spec.
- "table" → user asks for DATA, lists, comparisons, missing values, etc.
  Fill operation.
- "text" → for advice, explanations, follow-ups, and general conversation.
  MATCH your reply length to the question:
  • Simple/short question → 1-3 sentences
  • Moderate question → a solid paragraph
  • Complex/detailed request → multiple paragraphs with structure
  • If user asks for brevity ("make it short", "briefly") → BE CONCISE

RULES FOR "text" RESPONSES:
- Match the user's tone and complexity. Do NOT over-explain simple things.
- For follow-ups: read history, build on previous answers, NEVER repeat yourself.
- If the user asks you to shorten or simplify, DO IT.
- Be natural and conversational — like a real person, not a template.

EXAMPLES:
- "What is the churn rate?" → response_type: "kpi"
- "Show churn by geography" → response_type: "chart"
- "Show missing values" → response_type: "table"
- "How can I reduce churn?" → response_type: "text", give actionable strategy
- "Make it shorter" → response_type: "text", give a brief summary
- "Change to pie chart" → response_type: "chart", use previous context


For follow-up requests, ALWAYS read the conversation history and provide NEW information.
Set unused fields to null."""

# ─── Chart Explanation ───────────────────────────────────

CHART_EXPLANATION_PROMPT = """Explain this chart in simple business terms.

Chart Title: {chart_title}
Chart Type: {chart_type}
X-axis: {x_label}
Y-axis: {y_label}
Data Points: {data_summary}

Provide a 2-3 sentence explanation a business user would understand.
Highlight the key takeaway. Be specific with numbers.
Return plain text, not JSON."""

