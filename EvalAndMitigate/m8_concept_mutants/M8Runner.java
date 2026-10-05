import org.junit.runner.Description;
import org.junit.runner.JUnitCore;
import org.junit.runner.Request;
import org.junit.runner.Result;
import org.junit.internal.builders.AllDefaultPossibilitiesBuilder;

/** m8: runs single test methods (args: Class::method ...) and prints one line per test:
 *  M8T <tab> test <tab> PASS|FAIL|NORUN|TIMEOUT|ERROR <tab> exception class: message (normalised, <= 300 chars).
 *  suite() methods are ignored (JUnit3 classes run as plain TestCases). Each test runs in its own thread with a timeout. */
public class M8Runner {
    static String norm(String s) {
        s = String.valueOf(s).replaceAll("@[0-9a-f]{4,}", "@?").replaceAll("\\s+", " ");
        return s.length() > 300 ? s.substring(0, 300) : s;
    }

    public static void main(String[] args) throws Exception {
        long limit = Long.parseLong(System.getProperty("m8.timeout", "10000"));
        for (String t : args) {
            String[] p = t.split("::");
            final String[] res = {"ERROR", ""};
            Thread th = new Thread(() -> {
                try {
                    Class<?> c = Class.forName(p[0]);
                    Request req = Request.runner(new AllDefaultPossibilitiesBuilder(false).runnerForClass(c))
                            .filterWith(Description.createTestDescription(c, p[1]));
                    Result r = new JUnitCore().run(req);
                    if (r.getRunCount() == 0 || (r.getFailureCount() == 1 && String.valueOf(r.getFailures().get(0).getMessage()).startsWith("No tests found matching"))) {
                        res[0] = "NORUN";
                    } else if (r.wasSuccessful()) {
                        res[0] = "PASS";
                    } else {
                        Throwable e = r.getFailures().get(0).getException();
                        res[0] = "FAIL";
                        res[1] = e.getClass().getName() + ": " + e.getMessage();
                    }
                } catch (Throwable e) {
                    res[0] = "ERROR";
                    res[1] = e.toString();
                }
            });
            th.setDaemon(true);
            th.start();
            th.join(limit);
            boolean alive = th.isAlive();
            String status = alive ? "TIMEOUT" : res[0], msg = alive ? "" : res[1];
            if (alive) th.stop();
            System.out.println("M8T\t" + t + "\t" + status + "\t" + norm(msg));
            System.out.flush();
        }
        System.exit(0);
    }
}
