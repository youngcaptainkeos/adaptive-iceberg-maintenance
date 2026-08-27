import java.io.FileWriter;
import java.io.PrintWriter;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;

public class TelemetryExtractor {
    public static void main(String[] args) {
        if (args.length < 2) {
            System.err.println("Usage: java TelemetryExtractor <db_path> <output_csv_path>");
            System.exit(1);
        }
        
        String dbPath = args[0];
        String outputPath = args[1];
        
        System.out.println("Connecting to DuckDB telemetry database at " + dbPath + "...");
        
        String url = "jdbc:duckdb:" + dbPath;
        
        try (Connection conn = DriverManager.getConnection(url);
             Statement stmt = conn.createStatement()) {
            
            // Register JDBC driver explicitly just in case
            Class.forName("org.duckdb.DuckDBDriver");
            
            System.out.println("Querying experiment_telemetry...");
            String query = "SELECT run_id, event_id, event_status, event_start_time, event_end_time " +
                           "FROM experiment_telemetry " +
                           "WHERE event_type = 'EXEC_STATEMENT' " +
                           "ORDER BY event_start_time ASC";
            
            try (ResultSet rs = stmt.executeQuery(query);
                 PrintWriter writer = new PrintWriter(new FileWriter(outputPath))) {
                
                // Write CSV header
                writer.println("run_id,statement_id,status,start_time,end_time");
                
                int count = 0;
                while (rs.next()) {
                    String runId = rs.getString("run_id");
                    String eventId = rs.getString("event_id");
                    String status = rs.getString("event_status");
                    String startTime = rs.getString("event_start_time");
                    String endTime = rs.getString("event_end_time");
                    
                    // Simple CSV escaping: just replace any quotes/commas if they exist
                    runId = escapeCSV(runId);
                    eventId = escapeCSV(eventId);
                    status = escapeCSV(status);
                    startTime = escapeCSV(startTime);
                    endTime = escapeCSV(endTime);
                    
                    writer.println(runId + "," + eventId + "," + status + "," + startTime + "," + endTime);
                    count++;
                }
                
                System.out.println("Successfully extracted " + count + " records to " + outputPath);
            }
            
        } catch (Exception e) {
            System.err.println("Error extracting telemetry: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }
    
    private static String escapeCSV(String value) {
        if (value == null) {
            return "";
        }
        if (value.contains(",") || value.contains("\"") || value.contains("\n")) {
            return "\"" + value.replace("\"", "\"\"") + "\"";
        }
        return value;
    }
}
