import java.util.HashSet;
import java.util.Set;
import org.junit.runner.Description;
import org.junit.runner.JUnitCore;
import org.junit.runner.Request;
import org.junit.runner.notification.Failure;
import org.junit.runner.notification.RunListener;
import org.junit.internal.builders.AllDefaultPossibilitiesBuilder;

/** m10: runs whole test classes (arg "Class") or single test methods ("Class::method"), each item in its own thread
 *  with a timeout (-Dm10.timeout, ms). Prints one line per finished test:  M10T <tab> Class::method <tab> PASS|FAIL,
 *  and  M10C <tab> item <tab> TIMEOUT|ERROR  for an item that hangs or cannot be loaded (its unfinished tests print
 *  nothing, so the caller sees them as missing; after the first hang the limit drops to 10 s). suite() methods are
 *  ignored (JUnit 3 classes run as plain TestCases),
 *  as in m8's M8Runner. */
public class M10Runner {
    public static void main(String[] args) throws Exception {
        long limit = Long.parseLong(System.getProperty("m10.timeout", "180000"));
        for (String t : args) {
            final String[] p = t.split("::");
            Thread th = new Thread(() -> {
                try {
                    Class<?> c = Class.forName(p[0]);
                    Request req = Request.runner(new AllDefaultPossibilitiesBuilder(false).runnerForClass(c));
                    if (p.length > 1) req = req.filterWith(Description.createTestDescription(c, p[1]));
                    JUnitCore core = new JUnitCore();
                    core.addListener(new RunListener() {
                        final Set<Description> failed = new HashSet<>();
                        @Override public void testFailure(Failure f) { failed.add(f.getDescription()); }
                        @Override public void testFinished(Description d) {
                            System.out.println("M10T\t" + d.getClassName() + "::" + d.getMethodName() + "\t" + (failed.contains(d) ? "FAIL" : "PASS"));
                        }
                    });
                    core.run(req);
                } catch (Throwable e) {
                    System.out.println("M10C\t" + t + "\tERROR");
                }
            });
            th.setDaemon(true);
            th.start();
            th.join(limit);
            if (th.isAlive()) {
                System.out.println("M10C\t" + t + "\tTIMEOUT");
                limit = Math.min(limit, 10000);  // a candidate that hangs is rejected anyway: do not wait the full limit per class
                try { th.stop(); } catch (Throwable e) { }  // Java 20+ refuses stop(): the daemon thread is left behind
            }
            System.out.flush();
        }
        System.exit(0);
    }
}
