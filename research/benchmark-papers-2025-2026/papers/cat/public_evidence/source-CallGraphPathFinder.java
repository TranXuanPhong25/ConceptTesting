package org.example;

import sootup.callgraph.CallGraph;
import sootup.callgraph.CallGraphAlgorithm;
import sootup.callgraph.ClassHierarchyAnalysisAlgorithm;
import sootup.core.inputlocation.AnalysisInputLocation;
import sootup.core.signatures.MethodSignature;
import sootup.java.bytecode.frontend.inputlocation.DefaultRuntimeAnalysisInputLocation;
import sootup.java.bytecode.frontend.inputlocation.JavaClassPathAnalysisInputLocation;
import sootup.java.core.views.JavaView;

import java.io.BufferedWriter;
import java.io.BufferedReader;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;
import java.util.stream.Stream;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

public class CallGraphPathFinder {
    private enum RootMode { ALL, PUBLIC, MAINS }
    private String projectPackagePrefix = ""; 
    private String projectRootPrefix = "";  

    public static void main(String[] args) throws Exception {
        System.setProperty("org.slf4j.simpleLogger.defaultLogLevel", "error");
        System.setProperty("org.slf4j.simpleLogger.log.sootup", "error");
        System.setProperty("org.slf4j.simpleLogger.showDateTime", "false");

        if (args.length < 3) {
            System.err.println("Usage: [--roots=ALL|PUBLIC|MAINS] [--limitPackageRoots=true|false] [--depDir=<path>] <classpath> <targetClassFQN> <targetMethodName> [maxDepth=3] [outputFile]");
            return;
        }
        int index = 0;
        RootMode mode = RootMode.PUBLIC; 
        boolean limitPackageRoots = false;
        String depDir = null;
        while (index < args.length && args[index].startsWith("--")) {
            String opt = args[index];
            if (opt.startsWith("--roots=")) {
                String v = opt.substring("--roots=".length()).toUpperCase(Locale.ROOT);
                try { mode = RootMode.valueOf(v); } catch (IllegalArgumentException e) { System.err.println("Unknown root mode " + v + ", defaulting to PUBLIC"); }
                index++;
            } else if (opt.startsWith("--limitPackageRoots=")) {
                String v = opt.substring("--limitPackageRoots=".length()).toLowerCase(Locale.ROOT);
                limitPackageRoots = !("false".equals(v) || "0".equals(v) || "no".equals(v));
                index++;
            } else if (opt.startsWith("--depDir=")) {
                depDir = opt.substring("--depDir=".length());
                index++;
            } else {
                break;
            }
        }
        if (args.length - index < 3) {
            System.err.println("Usage: [--roots=ALL|PUBLIC|MAINS] [--limitPackageRoots=true|false] [--depDir=<path>] <classpath> <targetClassFQN> <targetMethodName> [maxDepth=7] [outputFile]");
            return;
        }
        String classPath = args[index++];
        String targetClass = args[index++];
        String targetMethodName = args[index++];
        
        // Smart parsing: check if next arg is a number (maxDepth) or a string (outputFile)
        int maxDepth = 3; // default
        String outputFile = "call_paths.txt"; // default
        
        if (args.length - index >= 1) {
            String nextArg = args[index];
            try {
                maxDepth = Integer.parseInt(nextArg);
                index++;
                if (args.length - index >= 1) {
                    outputFile = args[index];
                }
            } catch (NumberFormatException e) {
                outputFile = nextArg;
            }
        }
        new CallGraphPathFinder().run(classPath, targetClass, targetMethodName, maxDepth, outputFile, mode, limitPackageRoots, depDir);
    }

    private void run(String classPath, String targetClassFQN, String targetMethodName, int maxDepth, String outputFile, RootMode rootMode, boolean limitPackageRoots, String depDir) throws IOException {
        long start = System.currentTimeMillis();
        System.out.println("Phase 1: Analyzing main classpath to identify external dependencies...");
        Set<String> externalClasses = new LinkedHashSet<>();
        String enhancedClassPath = classPath;
        
        if (depDir != null && !depDir.isEmpty()) {
            JavaView quickView = buildViewNoAutoDeps(classPath);
            Set<String> knownClasses = new HashSet<>();
            quickView.getClasses().forEach(sc -> knownClasses.add(sc.getClassSource().getClassType().getFullyQualifiedName()));
            
            for (var sc : quickView.getClasses().collect(Collectors.toList())) {
                for (var m : sc.getMethods()) {
                    String sub = m.getSubSignature().toString();
                    int l = sub.indexOf('(');
                    int r = sub.lastIndexOf(')');
                    if (l >= 0 && r > l) {
                        String params = sub.substring(l + 1, r).trim();
                        if (!params.isEmpty()) {
                            for (String param : params.split(",")) {
                                String pType = param.trim();
                                while (pType.endsWith("[]")) pType = pType.substring(0, pType.length() - 2).trim();
                                if (!isPrimitiveName(pType) && !knownClasses.contains(pType) && !pType.startsWith("java.lang.")) {
                                    externalClasses.add(pType);
                                }
                            }
                        }
                    }
                }
            }
            
            if (!externalClasses.isEmpty()) {
                System.out.println("Found " + externalClasses.size() + " external classes referenced:");
                for (String ext : externalClasses) {
                    System.out.println("  - " + ext);
                }
                Map<String, Set<String>> jarToClasses = scanJarsForClasses(depDir, externalClasses);
                
                if (!jarToClasses.isEmpty()) {
                    System.out.println("\nRequired dependency JARs:");
                    StringBuilder additionalCp = new StringBuilder();
                    for (Map.Entry<String, Set<String>> e : jarToClasses.entrySet()) {
                        System.out.println("  " + e.getKey() + " (provides: " + String.join(", ", e.getValue()) + ")");
                        if (additionalCp.length() > 0) additionalCp.append(":");
                        additionalCp.append(e.getKey());
                    }
                    enhancedClassPath = classPath + ":" + additionalCp;
                    System.out.println("\nPhase 2: Re-analyzing with required dependencies...");
                } else {
                    System.out.println("No JARs found containing the external classes in " + depDir);
                }
            }
        }
        
        JavaView view = buildViewNoAutoDeps(enhancedClassPath);
        String resolvedTargetClassFQN = resolveClassFQN(view, targetClassFQN, targetMethodName);
        final var classesListAll = view.getClasses().collect(Collectors.toList());
        for (var sc : classesListAll) {
            String classFqn = sc.getClassSource().getClassType().getFullyQualifiedName();
            try {
                String cvis;
                if (sc.isPublic()) cvis = "public";
                else if (sc.isProtected()) cvis = "protected";
                else if (sc.isPrivate()) cvis = "private";
                else cvis = "default";
                boolean isAbs = false;
                boolean isFinal = false;
                try { isAbs = sc.isAbstract(); } catch (Throwable ignored) {}
                try { isFinal = sc.isFinal(); } catch (Throwable ignored) {}
                StringBuilder mods = new StringBuilder(cvis);
                if (isFinal) mods.append(" final");
                if (isAbs) mods.append(" abstract");
                classModifiers.put(classFqn, mods.toString());
                if (sc.isPublic()) {
                    try {
                        //superclass
                        var superOpt = sc.getSuperclass();
                        if (superOpt.isPresent()) {
                            String superFqn = superOpt.get().getFullyQualifiedName();
                            if (!superFqn.equals("java.lang.Object")) {
                                implementationsOf.computeIfAbsent(superFqn, k -> new ArrayList<>()).add(classFqn);
                            }
                        }
                        for (var iface : sc.getInterfaces()) {
                            String ifaceFqn = iface.getFullyQualifiedName();
                            implementationsOf.computeIfAbsent(ifaceFqn, k -> new ArrayList<>()).add(classFqn);
                        }
                    } catch (Throwable ignored) {}
                }
            } catch (Throwable t) {
                classModifiers.put(classFqn, "");
            }
            for (var m : sc.getMethods()) {
                String vis;
                if (m.isPublic()) vis = "public"; else if (m.isProtected()) vis = "protected"; else if (m.isPrivate()) vis = "private"; else vis = "default";
                methodModifiers.put(buildKey(m.getSignature()), vis);
                if ("<init>".equals(m.getName())) {
                    String sub = m.getSubSignature().toString();
                    int l = sub.indexOf('(');
                    int r = sub.lastIndexOf(')');
                    String params = (l >= 0 && r >= 0 && r > l) ? sub.substring(l + 1, r).trim() : "";
                    constructorsByClass.computeIfAbsent(classFqn, k -> new ArrayList<>()).add(params);
                    constructorModsByClass.computeIfAbsent(classFqn, k -> new ArrayList<>()).add(vis);
                }
                if (m.isPublic() && m.isStatic() && !m.getName().startsWith("<")) {
                    try {
                        String sub = m.getSubSignature().toString();
                        int spaceIdx = sub.indexOf(' ');
                        if (spaceIdx > 0) {
                            String returnType = sub.substring(0, spaceIdx);
                            if (!returnType.equals("void") && !isPrimitiveName(returnType)) {
                                String baseReturn = returnType;
                                while (baseReturn.endsWith("[]")) baseReturn = baseReturn.substring(0, baseReturn.length() - 2);
                                if (!isPrimitiveName(baseReturn)) {
                                    String methodDesc = classFqn + "#" + sub.substring(spaceIdx + 1) + ": " + returnType;
                                    factoryMethodsFor.computeIfAbsent(baseReturn, k -> new ArrayList<>()).add(methodDesc);
                                }
                            }
                        }
                    } catch (Throwable ignored) {}
                }
            }
        }

    String targetPkgPrefix = "";
    int lastDotIdx = resolvedTargetClassFQN.lastIndexOf('.');
    if (lastDotIdx > 0) targetPkgPrefix = resolvedTargetClassFQN.substring(0, lastDotIdx);
    this.projectPackagePrefix = targetPkgPrefix;
    this.projectRootPrefix = computeProjectRootPrefix(resolvedTargetClassFQN);
    List<MethodSignature> entryPoints = selectRoots(view, rootMode, limitPackageRoots ? targetPkgPrefix : "");
        if (entryPoints.isEmpty()) {
            System.err.println("No entry points discovered under mode=" + rootMode + ". Aborting.");
            return;
        }

        CallGraphAlgorithm cha = new ClassHierarchyAnalysisAlgorithm(view);
        CallGraph cg = cha.initialize(entryPoints);

    Map<MethodSignature, Set<MethodSignature>> forward = new HashMap<>();
    cg.getCalls().forEach(call -> forward.computeIfAbsent(call.sourceMethodSignature(), k -> new LinkedHashSet<>()).add(call.targetMethodSignature()));

        List<MethodSignature> targets = new ArrayList<>();
        final var classesList = view.getClasses().collect(Collectors.toList());
        for (var sc : classesList) {
            String fqn = sc.getClassSource().getClassType().getFullyQualifiedName();
            if (fqn.equals(resolvedTargetClassFQN)) {
                for (var m : sc.getMethods()) {
                    if (m.getName().equals(targetMethodName)) {
                        targets.add(m.getSignature());
                    }
                }
            }
        }
        if (targets.isEmpty()) {
            System.err.println("No target methods resolved for " + resolvedTargetClassFQN + "." + targetMethodName);
            return;
        }

        Set<MethodSignature> canReachTarget = new HashSet<>(targets);
        boolean changed;
        do {
            changed = false;
            for (Map.Entry<MethodSignature, Set<MethodSignature>> e : forward.entrySet()) {
                if (!canReachTarget.contains(e.getKey())) {
                    for (MethodSignature t : e.getValue()) {
                        if (canReachTarget.contains(t)) {
                            canReachTarget.add(e.getKey());
                            changed = true;
                            break;
                        }
                    }
                }
            }
        } while (changed);

    int totalPaths = writePathsIterative(outputFile, forward, entryPoints, canReachTarget, new HashSet<>(targets), rootMode, resolvedTargetClassFQN, targetMethodName, maxDepth, limitPackageRoots);
        long elapsed = System.currentTimeMillis() - start;
        System.out.printf("Found %d paths (depth<=%d) ending in target(s) using roots=%s in %d ms. Target class: %s Output: %s%n", totalPaths, maxDepth, rootMode, elapsed, resolvedTargetClassFQN, outputFile);
    }

    private String resolveClassFQN(JavaView view, String userProvided, String targetMethodName) {
        if (userProvided.contains(".")) {
            return userProvided; 
        }
        String simple = userProvided;
        List<String> matches = new ArrayList<>();
        final var classesList = view.getClasses().collect(Collectors.toList());
        for (var sc : classesList) {
            String fqn = sc.getClassSource().getClassType().getFullyQualifiedName();
            if (simpleName(fqn).equals(simple)) {
                matches.add(fqn);
            }
        }
        if (matches.isEmpty()) {
            System.err.println("Could not resolve simple class name '" + simple + "' on classpath. Proceeding with original value (may fail): " + userProvided);
            return userProvided;
        }
        if (matches.size() > 1 && targetMethodName != null && !targetMethodName.isEmpty()) {
            List<String> narrowed = new ArrayList<>();
            for (var sc : classesList) {
                String fqn = sc.getClassSource().getClassType().getFullyQualifiedName();
                if (matches.contains(fqn)) {
                    boolean hasMethod = false;
                    for (var m : sc.getMethods()) {
                        if (m.getName().equals(targetMethodName)) { hasMethod = true; break; }
                    }
                    if (hasMethod) narrowed.add(fqn);
                }
            }
            if (!narrowed.isEmpty()) {
                matches = narrowed;
            }
        }
        if (matches.size() > 1) {
            System.err.println("Ambiguous simple class name '" + simple + "' resolved to multiple FQNs: " + matches + ". Using first: " + matches.get(0));
        }
        return matches.get(0);
    }

    private String simpleName(String fqn) {
        int lastDot = fqn.lastIndexOf('.');
        return lastDot >= 0 ? fqn.substring(lastDot + 1) : fqn;
    }

    private List<MethodSignature> selectRoots(JavaView view, RootMode mode, String packagePrefix) {
        List<MethodSignature> roots = new ArrayList<>();
        final String pkg = packagePrefix == null ? "" : packagePrefix;
        final var classesList = view.getClasses().collect(Collectors.toList());
        switch (mode) {
            case MAINS -> {
                for (var sc : classesList) {
                    String fqn = sc.getClassSource().getClassType().getFullyQualifiedName();
                    if (!pkg.isEmpty() && !fqn.startsWith(pkg)) continue;
                    for (var m : sc.getMethods()) {
                        if (m.isPublic() && m.getName().equals("main")) roots.add(m.getSignature());
                    }
                }
            }
            case PUBLIC -> {
                for (var sc : classesList) {
                    String fqn = sc.getClassSource().getClassType().getFullyQualifiedName();
                    if (!pkg.isEmpty() && !fqn.startsWith(pkg)) continue;
                    for (var m : sc.getMethods()) {
                        if (m.isPublic()) roots.add(m.getSignature());
                    }
                }
            }
            case ALL -> {
                for (var sc : classesList) {
                    String fqn = sc.getClassSource().getClassType().getFullyQualifiedName();
                    if (!pkg.isEmpty() && !fqn.startsWith(pkg)) continue;
                    for (var m : sc.getMethods()) {
                        roots.add(m.getSignature());
                    }
                }
            }
        }
        return roots;
    }

    private JavaView buildView(String classPath) {
        List<AnalysisInputLocation> inputs = new ArrayList<>();
        Set<String> added = new LinkedHashSet<>();

        for (String rawEntry : classPath.split(":")) {
            if (rawEntry == null || rawEntry.trim().isEmpty()) continue;
            if (rawEntry.contains("*")) {
                expandWildcard(rawEntry).forEach(p -> addInput(p.toString(), inputs, added));
                continue;
            }

            Path entry = Paths.get(rawEntry);
            if (Files.exists(entry)) {
                addInput(entry.toString(), inputs, added);
                if (Files.isDirectory(entry)) {
                    autoAddDependencyDirs(entry, inputs, added);
                }
            } else {
                System.err.println("Warning: classpath entry not found: " + rawEntry);
            }
        }
        inputs.add(new DefaultRuntimeAnalysisInputLocation());
        System.out.println("Resolved classpath entries (" + added.size() + "): ");
        for (String s : added) System.out.println("  " + s);

        return new JavaView(inputs);
    }

    private JavaView buildViewNoAutoDeps(String classPath) {
        List<AnalysisInputLocation> inputs = new ArrayList<>();
        Set<String> added = new LinkedHashSet<>();

        for (String rawEntry : classPath.split(":")) {
            if (rawEntry == null || rawEntry.trim().isEmpty()) continue;
            if (rawEntry.contains("*")) {
                expandWildcard(rawEntry).forEach(p -> addInput(p.toString(), inputs, added));
                continue;
            }

            Path entry = Paths.get(rawEntry);
            if (Files.exists(entry)) {
                addInput(entry.toString(), inputs, added);
            } else {
                System.err.println("Warning: classpath entry not found: " + rawEntry);
            }
        }
        inputs.add(new DefaultRuntimeAnalysisInputLocation());
        System.out.println("Resolved classpath entries (" + added.size() + "): ");
        for (String s : added) System.out.println("  " + s);
        return new JavaView(inputs);
    }

    private Map<String, Set<String>> scanJarsForClasses(String depDir, Set<String> targetClasses) {
        Map<String, Set<String>> result = new LinkedHashMap<>();
        Path depPath = Paths.get(depDir);

        if (!Files.isDirectory(depPath)) {
            System.err.println("Dependency directory not found: " + depDir);
            return result;
        }
        Map<String, String> classToPath = new HashMap<>();
        Map<String, String> pathToClass = new HashMap<>();
        for (String cls : targetClasses) {
            String path = cls.replace('.', '/') + ".class";
            classToPath.put(cls, path);
            pathToClass.put(path, cls);
        }
        Set<String> foundClasses = new HashSet<>();
        Set<String> targetPaths = new HashSet<>(pathToClass.keySet());

        try (Stream<Path> walk = Files.walk(depPath, 2)) {
            List<Path> jars = walk.filter(p -> p.toString().endsWith(".jar")).collect(Collectors.toList());

            for (Path jarPath : jars) {
                if (foundClasses.size() == targetClasses.size()) {
                    break; 
                }
                Set<String> providedClasses = new LinkedHashSet<>();
                try (JarFile jar = new JarFile(jarPath.toFile())) {
                    Enumeration<JarEntry> entries = jar.entries();
                    while (entries.hasMoreElements()) {
                        JarEntry entry = entries.nextElement();
                        String entryName = entry.getName();
                        if (!entryName.endsWith(".class")) {
                            continue;
                        }
                        if (targetPaths.contains(entryName)) {
                            String cls = pathToClass.get(entryName);
                            if (cls != null && !foundClasses.contains(cls)) {
                                providedClasses.add(cls);
                                foundClasses.add(cls);
                            }
                        }
                    }
                } catch (IOException e) {
                    System.err.println("Warning: Could not read JAR " + jarPath + ": " + e.getMessage());
                }

                if (!providedClasses.isEmpty()) {
                    result.put(jarPath.toString(), providedClasses);
                }
            }
        } catch (IOException e) {
            System.err.println("Error scanning dependency directory: " + e.getMessage());
        }

        Set<String> notFound = new LinkedHashSet<>(targetClasses);
        notFound.removeAll(foundClasses);
        if (!notFound.isEmpty()) {
            System.out.println("Classes not found in any JAR (may be JDK classes or missing):");
            for (String cls : notFound) {
                System.out.println("  - " + cls);
            }
        }

        return result;
    }

    private void maybePrepareMaven(Path classesDir) {
        ;
    }

    private void maybeAddMavenClasspath(Path classesDir, List<AnalysisInputLocation> inputs, Set<String> added) {
        ;
    }

    private boolean isDirEmpty(Path dir) {
        try (Stream<Path> s = Files.list(dir)) {
            return !s.findAny().isPresent();
        } catch (IOException e) {
            return true;
        }
    }

    private boolean hasAnyJarUnder(Path dir, int maxDepth) {
        try (Stream<Path> s = Files.walk(dir, maxDepth)) {
            return s.anyMatch(p -> p.toString().endsWith(".jar"));
        } catch (IOException e) {
            return false;
        }
    }

    private boolean runCmd(List<String> cmd, Path workDir, long timeoutSeconds) {
        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.directory(workDir.toFile());
        pb.redirectErrorStream(true);
        try {
            Process p = pb.start();
            Thread t = new Thread(() -> {
                try (BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream()))) {
                    String line;
                    while ((line = br.readLine()) != null) {
                        System.out.println("[auto-maven] " + line);
                    }
                } catch (IOException ignored) {}
            });
            t.setDaemon(true);
            t.start();
            boolean finished = p.waitFor(timeoutSeconds, TimeUnit.SECONDS);
            if (!finished) {
                p.destroyForcibly();
                System.err.println("[auto-maven] Command timed out: " + String.join(" ", cmd));
                return false;
            }
            int code = p.exitValue();
            if (code != 0) {
                System.err.println("[auto-maven] Command failed (" + code + "): " + String.join(" ", cmd));
                return false;
            }
            return true;
        } catch (Exception e) {
            System.err.println("[auto-maven] Failed to run command: " + e + ": " + String.join(" ", cmd));
            return false;
        }
    }

    private void addInput(String path, List<AnalysisInputLocation> inputs, Set<String> added) {
        if (added.contains(path)) return;
        inputs.add(new JavaClassPathAnalysisInputLocation(path));
        added.add(path);
    }

    private List<Path> expandWildcard(String pattern) {
        List<Path> out = new ArrayList<>();
        try {
            if (pattern.endsWith("/*")) {
                Path dir = Paths.get(pattern.substring(0, pattern.length() - 2));
                if (Files.isDirectory(dir)) {
                    try (Stream<Path> stream = Files.list(dir)) {
                        stream.filter(p -> p.toString().endsWith(".jar") || Files.isDirectory(p))
                              .forEach(out::add);
                    }
                }
            } else if (pattern.contains("**")) {
                String baseStr = pattern.substring(0, pattern.indexOf("**"));
                Path base = Paths.get(baseStr);
                if (Files.isDirectory(base)) {
                    try (Stream<Path> walk = Files.walk(base, 5)) {
                        walk.filter(p -> p.toString().endsWith(".jar")).forEach(out::add);
                    }
                }
            } else {
                Path p = Paths.get(pattern);
                if (Files.exists(p)) out.add(p);
            }
        } catch (IOException ignored) {
        }
        return out;
    }

    private void autoAddDependencyDirs(Path classesDir, List<AnalysisInputLocation> inputs, Set<String> added) {
        List<Path> candidates = new ArrayList<>();
        Path base = classesDir.getParent() != null ? classesDir.getParent() : classesDir;
    String[] names = new String[]{
        "dependency", "dependencies", "deps", "lib", "libs"
    };
        for (String n : names) {
            candidates.add(base.resolve(n));
        }
        for (Path cand : candidates) {
            if (!Files.isDirectory(cand)) continue;
            try (Stream<Path> walk = Files.walk(cand, 2)) {
                walk.filter(p -> p.toString().endsWith(".jar"))
                    .forEach(p -> addInput(p.toString(), inputs, added));
            } catch (IOException ignored) {
            }
        }
    }

    private int writePathsIterative(String file,
                                    Map<MethodSignature, Set<MethodSignature>> forward,
                                    List<MethodSignature> roots,
                                    Set<MethodSignature> canReachTarget,
                                    Set<MethodSignature> targets,
                                    RootMode mode,
                                    String targetClass,
                                    String targetMethod,
                                    int maxDepth,
                                    boolean limitPackageRoots) throws IOException {
        int total = 0;
        Set<String> seenPathOutputs = new HashSet<>();
        LinkedHashSet<String> allInitClasses = new LinkedHashSet<>();
        
        allInitClasses.add(targetClass);
        
        List<Deque<MethodSignature>> allPaths = new ArrayList<>();
        for (MethodSignature root : roots) {
            findAllPathsUpToDepth(forward, root, targets, maxDepth, 0, new ArrayDeque<>(), new HashSet<>(), allPaths);
        }

        List<String> uniquePathStrings = new ArrayList<>();
        for (Deque<MethodSignature> stack : allPaths) {
            String pathStr = formatSinglePathAndCollectInits(stack, allInitClasses, targets);
            if (!pathStr.isEmpty() && !seenPathOutputs.contains(pathStr)) {
                uniquePathStrings.add(pathStr);
                seenPathOutputs.add(pathStr);
            }
        }
        if (uniquePathStrings.isEmpty()) {
            for (MethodSignature t : targets) {
                if (t.getDeclClassType().getFullyQualifiedName().equals(targetClass)
                    && t.getName().equals(targetMethod)) {
                    ArrayDeque<MethodSignature> self = new ArrayDeque<>();
                    self.addLast(t);
                    String pathStr = formatSinglePathAndCollectInits(self, allInitClasses, targets);
                    if (!pathStr.isEmpty() && !seenPathOutputs.contains(pathStr)) {
                        uniquePathStrings.add(pathStr);
                        seenPathOutputs.add(pathStr);
                    }
                }
            }
        }
        total = uniquePathStrings.size();

        try (BufferedWriter bw = new BufferedWriter(new FileWriter(file))) {
            bw.write("# Target: " + targetClass + "." + targetMethod + "\n");
            bw.write("# Roots: " + mode + ", MaxDepth: " + maxDepth + ", LimitPackageRoots: " + limitPackageRoots + "\n");
            bw.flush();

            if (!uniquePathStrings.isEmpty()) {
                bw.write("## Max Depth Paths\n");
                for (String p : uniquePathStrings) bw.write(p);
                bw.flush();
            } else {
                bw.write("## No Public Paths Found\n");
                bw.write("# Note: No public methods in public classes can reach the target method within maxDepth.\n");
                bw.write("# The target method may be non-public or only reachable via non-public paths.\n");
                bw.write("# Initialization information for the target class is provided below.\n\n");
                bw.flush();
            }
            LinkedHashSet<String> expandedInitClasses = new LinkedHashSet<>(allInitClasses);
            boolean foundNew;
            do {
                foundNew = false;
                LinkedHashSet<String> toAdd = new LinkedHashSet<>();
                for (String cls : expandedInitClasses) {
                    List<String> ctors = constructorsByClass.getOrDefault(cls, Collections.emptyList());
                    List<String> ctorMods = constructorModsByClass.getOrDefault(cls, Collections.emptyList());
                    for (int i = 0; i < ctors.size(); i++) {
                        String mod = i < ctorMods.size() ? ctorMods.get(i) : "";
                        if (!"public".equals(mod)) continue; 
                        String paramsCsv = ctors.get(i);
                        for (String pType : extractParamTypes(paramsCsv)) {
                            if (expandedInitClasses.contains(pType) || toAdd.contains(pType)) continue;
                            toAdd.add(pType);
                            foundNew = true;
                        }
                    }
                }
                expandedInitClasses.addAll(toAdd);
            } while (foundNew);
            
            bw.write("\n## All Initializations\n");
            List<String> initLines = buildInitializationLines(expandedInitClasses);
            if (initLines.isEmpty()) {
                bw.write("# No public class initializations found for target class.\n");
            } else {
                for (String line : initLines) {
                    bw.write(line);
                    bw.write("\n");
                }
            }
            bw.flush();
        }
        return total;
    }

    private void findAllPathsUpToDepth(Map<MethodSignature, Set<MethodSignature>> forward,
                                       MethodSignature current,
                                       Set<MethodSignature> targets,
                                       int depthLimit,
                                       int currentDepth,
                                       Deque<MethodSignature> stack,
                                       Set<MethodSignature> onPath,
                                       List<Deque<MethodSignature>> out) {
        stack.addLast(current);
        onPath.add(current);
        if (targets.contains(current) && currentDepth <= depthLimit) {
            out.add(new ArrayDeque<>(stack));
        }
        if (currentDepth < depthLimit) {
            for (MethodSignature succ : forward.getOrDefault(current, Collections.emptySet())) {
                if (onPath.contains(succ)) continue;
                findAllPathsUpToDepth(forward, succ, targets, depthLimit, currentDepth + 1, stack, onPath, out);
            }
        }
        stack.removeLast();
        onPath.remove(current);
    }

    private String formatSinglePathAndCollectInits(Deque<MethodSignature> stack, LinkedHashSet<String> allInitClasses, Set<MethodSignature> targets) {
        StringBuilder sb = new StringBuilder();
        LinkedHashSet<String> classesOnPath = new LinkedHashSet<>();
        
        List<MethodSignature> methodsToPrint = new ArrayList<>();
        for (MethodSignature ms : stack) {
            String visibility = visibilityOf(ms);
            boolean isTarget = targets.contains(ms);
            
            if (isTarget) {
                classesOnPath.add(ms.getDeclClassType().getFullyQualifiedName());
                String subsig = ms.getSubSignature().toString();
                int lparen = subsig.indexOf('(');
                int rparen = subsig.lastIndexOf(')');
                if (lparen >= 0 && rparen > lparen) {
                    String params = subsig.substring(lparen + 1, rparen).trim();
                    if (!params.isEmpty()) {
                        for (String param : params.split(",")) {
                            String paramType = param.trim();
                            while (paramType.endsWith("[]")) {
                                paramType = paramType.substring(0, paramType.length() - 2).trim();
                            }
                            if (!isPrimitiveName(paramType)) {
                                classesOnPath.add(paramType);
                            }
                        }
                    }
                }
                if (!"public".equals(visibility)) {
                    continue;
                }
            }
            if ("public".equals(visibility)) {
                String declClass = ms.getDeclClassType().getFullyQualifiedName();
                String classMod = classModifiers.getOrDefault(declClass, "").trim();
                if (!classMod.startsWith("public")) {
                    continue;
                }
                if (classMod.contains("abstract")) {
                    continue;
                }
                boolean hasUninstantiableParam = false;
                String subsig = ms.getSubSignature().toString();
                int lparen = subsig.indexOf('(');
                int rparen = subsig.lastIndexOf(')');
                if (lparen >= 0 && rparen > lparen) {
                    String params = subsig.substring(lparen + 1, rparen).trim();
                    if (!params.isEmpty()) {
                        for (String param : params.split(",")) {
                            String paramType = param.trim();
                            while (paramType.endsWith("[]")) {
                                paramType = paramType.substring(0, paramType.length() - 2).trim();
                            }
                            if (isPrimitiveName(paramType)) {
                                continue;
                            }
                            String paramMod = classModifiers.getOrDefault(paramType, "").trim();
                            if (paramMod.contains("abstract")) {
                                boolean hasUsableImpl = hasConcreteImplementation(paramType, new HashSet<>());
                                if (!hasUsableImpl) {
                                    hasUninstantiableParam = true;
                                    break;
                                }
                            }
                        }
                    }
                }
                if (!hasUninstantiableParam) {
                    methodsToPrint.add(ms);
                    classesOnPath.add(ms.getDeclClassType().getFullyQualifiedName());
                    if (lparen >= 0 && rparen > lparen) {
                        String params = subsig.substring(lparen + 1, rparen).trim();
                        if (!params.isEmpty()) {
                            for (String param : params.split(",")) {
                                String paramType = param.trim();
                                while (paramType.endsWith("[]")) {
                                    paramType = paramType.substring(0, paramType.length() - 2).trim();
                                }
                                if (!isPrimitiveName(paramType)) {
                                    classesOnPath.add(paramType);
                                }
                            }
                        }
                    }
                }
            }
        }
        if (methodsToPrint.isEmpty()) {
            return "";
        }
        LinkedHashSet<String> initClasses = new LinkedHashSet<>(classesOnPath);
        final int MAX_PARAM_CLOSURE_DEPTH = 2;
        String inProjectPrefix = (this.projectRootPrefix == null || this.projectRootPrefix.isEmpty())
            ? (this.projectPackagePrefix == null ? "" : this.projectPackagePrefix)
            : this.projectRootPrefix;
        Map<String, Integer> levelByClass = new HashMap<>();
        ArrayDeque<String> queue = new ArrayDeque<>();
        for (String c : initClasses) { levelByClass.put(c, 0); queue.add(c); }
        while (!queue.isEmpty()) {
            String cur = queue.pollFirst();
            int lvl = levelByClass.getOrDefault(cur, 0);
            if (lvl >= MAX_PARAM_CLOSURE_DEPTH) continue;
            List<String> ctors = constructorsByClass.getOrDefault(cur, Collections.emptyList());
            for (String paramsCsv : ctors) {
                for (String pType : extractParamTypes(paramsCsv)) {
                    if (!inProjectPrefix.isEmpty() && !pType.startsWith(inProjectPrefix)) continue;
                    if (!classModifiers.containsKey(pType) && !constructorsByClass.containsKey(pType)) continue;
                    if (initClasses.add(pType)) {
                        levelByClass.put(pType, lvl + 1);
                        queue.addLast(pType);
                    }
                }
            }
        }
        LinkedHashSet<String> publicInitClasses = new LinkedHashSet<>();
        for (String cls : initClasses) {
            String classMod = classModifiers.getOrDefault(cls, "").trim();
            if (classMod.startsWith("public")) {
                publicInitClasses.add(cls);
            }
        }
        allInitClasses.addAll(publicInitClasses);
        
        sb.append("Path:\n");
        for (MethodSignature ms : methodsToPrint) {
            sb.append("  ").append(formatSignature(ms)).append("\n");
        }
        sb.append("---\n");
        return sb.toString();
    }

    private List<String> buildInitializationLines(LinkedHashSet<String> initClasses) {
        List<String> initLines = new ArrayList<>();
        boolean firstPrinted = false;
        for (String cls : initClasses) {
            String classMod = classModifiers.getOrDefault(cls, "").trim();
            if (!classMod.isEmpty() && !classMod.startsWith("public")) {
                continue;
            }
            if (firstPrinted) {
                initLines.add("");
            }
            firstPrinted = true;

            List<String> ctors = constructorsByClass.getOrDefault(cls, Collections.emptyList());
            List<String> ctorMods = constructorModsByClass.getOrDefault(cls, Collections.emptyList());
            List<Integer> publicCtorIdxs = new ArrayList<>();
            for (int i = 0; i < ctors.size(); i++) {
                String mod = i < ctorMods.size() ? ctorMods.get(i) : "";
                if ("public".equals(mod)) publicCtorIdxs.add(i);
            }
            String modDisplay = classMod.isEmpty() ? "external" : classMod;
            initLines.add("  " + cls + " (" + modDisplay + "):");
            if (publicCtorIdxs.isEmpty()) {
                if (ctors.isEmpty() && classMod.isEmpty()) {
                    initLines.add("         external class - constructors unknown.");
                } else {
                    initLines.add("         no public constructors found.");
                }
            } else {
                for (int idx : publicCtorIdxs) {
                    String rawParams = ctors.get(idx);
                    String annotated = annotateParamModifiers(rawParams);
                    String simpleClassName = cls.contains(".") ? cls.substring(cls.lastIndexOf('.') + 1) : cls;
                    initLines.add("    " + simpleClassName + "(" + annotated + ") (public)");
                }
            }
            
            List<String> impls = implementationsOf.getOrDefault(cls, Collections.emptyList());
            if (!impls.isEmpty()) {
                Set<String> allImpls = new LinkedHashSet<>();
                collectAllImplementations(cls, allImpls, new HashSet<>());
                if (!allImpls.isEmpty()) {
                    initLines.add("    Known implementations:");
                    for (String impl : allImpls) {
                        String implMod = classModifiers.getOrDefault(impl, "").trim();
                        initLines.add("      - " + impl + (implMod.isEmpty() ? "" : " (" + implMod + ")"));
                    }
                }
            }
            
            List<String> factories = factoryMethodsFor.getOrDefault(cls, Collections.emptyList());
            if (!factories.isEmpty()) {
                initLines.add("    Factory methods:");
                for (String factory : factories) {
                    initLines.add("      - " + factory);
                }
            }
        }
        return initLines;
    }

    private void depthLimitedDfs(Map<MethodSignature, Set<MethodSignature>> forward,
                                 MethodSignature current,
                                 Set<MethodSignature> targets,
                                 int depthLimit,
                                 int currentDepth,
                                 Deque<MethodSignature> stack,
                                 Set<MethodSignature> onPath,
                                 List<String> out,
                                 Set<String> seenPathKeys) {
        stack.addLast(current);
        onPath.add(current);

        boolean isTarget = targets.contains(current);
        if (isTarget && currentDepth <= depthLimit) {
            if (currentDepth == depthLimit) {
                String key = buildPathKey(stack);
                if (!seenPathKeys.contains(key)) {
                    out.add(formatSinglePath(stack));
                    seenPathKeys.add(key);
                }
            }
        }
        if (currentDepth < depthLimit) {
            for (MethodSignature succ : forward.getOrDefault(current, Collections.emptySet())) {
                if (onPath.contains(succ)) continue;
                depthLimitedDfs(forward, succ, targets, depthLimit, currentDepth + 1, stack, onPath, out, seenPathKeys);
            }
        }
        stack.removeLast();
        onPath.remove(current);
    }

    private String formatSinglePath(Deque<MethodSignature> stack) {
        StringBuilder sb = new StringBuilder();
        LinkedHashSet<String> classesOnPath = new LinkedHashSet<>();
        for (MethodSignature ms : stack) {
            classesOnPath.add(ms.getDeclClassType().getFullyQualifiedName());
        }
        LinkedHashSet<String> initClasses = new LinkedHashSet<>(classesOnPath);
        final int MAX_PARAM_CLOSURE_DEPTH = 2;
    String inProjectPrefix = (this.projectRootPrefix == null || this.projectRootPrefix.isEmpty())
        ? (this.projectPackagePrefix == null ? "" : this.projectPackagePrefix)
        : this.projectRootPrefix;
        Map<String, Integer> levelByClass = new HashMap<>();
        ArrayDeque<String> queue = new ArrayDeque<>();
        for (String c : initClasses) { levelByClass.put(c, 0); queue.add(c); }
        while (!queue.isEmpty()) {
            String cur = queue.pollFirst();
            int lvl = levelByClass.getOrDefault(cur, 0);
            if (lvl >= MAX_PARAM_CLOSURE_DEPTH) continue;
            List<String> ctors = constructorsByClass.getOrDefault(cur, Collections.emptyList());
            for (String paramsCsv : ctors) {
                for (String pType : extractParamTypes(paramsCsv)) {
                    if (!inProjectPrefix.isEmpty() && !pType.startsWith(inProjectPrefix)) continue;
                    if (!classModifiers.containsKey(pType) && !constructorsByClass.containsKey(pType)) continue;
                    if (initClasses.add(pType)) {
                        levelByClass.put(pType, lvl + 1);
                        queue.addLast(pType);
                    }
                }
            }
        }
        List<String> initLines = new ArrayList<>();
        for (String cls : initClasses) {
            List<String> ctors = constructorsByClass.getOrDefault(cls, Collections.emptyList());
            List<String> ctorMods = constructorModsByClass.getOrDefault(cls, Collections.emptyList());
            if (!ctors.isEmpty()) {
                StringBuilder line = new StringBuilder();
                String classMod = classModifiers.getOrDefault(cls, "").trim();
                line.append("  ").append(cls);
                if (!classMod.isEmpty()) line.append(" (").append(classMod).append(")");
                line.append(": ");
                for (int i = 0; i < ctors.size(); i++) {
                    if (i > 0) line.append(", ");
                    String rawParams = ctors.get(i);
                    String annotated = annotateParamModifiers(rawParams);
                    line.append("(").append(annotated).append(")");
                    if (i < ctorMods.size()) {
                        String mod = ctorMods.get(i);
                        if (mod != null && !mod.isEmpty()) {
                            line.append(" (").append(mod).append(")");
                        }
                    }
                }
                line.append("\n");
                initLines.add(line.toString());
            }
        }
        if (!initLines.isEmpty()) {
            sb.append("Initializations:\n");
            for (String l : initLines) sb.append(l);
        }
        sb.append("Path:\n");
        for (MethodSignature ms : stack) {
            sb.append("  ").append(formatSignature(ms)).append("\n");
        }
        sb.append("---\n");
        return sb.toString();
    }

    private List<String> extractParamTypes(String paramsCsv) {
        if (paramsCsv == null || paramsCsv.isEmpty()) return Collections.emptyList();
        String[] parts = paramsCsv.split(",");
        List<String> out = new ArrayList<>(parts.length);
        for (String raw : parts) {
            String t = raw.trim();
            if (t.isEmpty()) continue;
            while (t.endsWith("[]")) t = t.substring(0, t.length() - 2);
            if (isPrimitiveName(t)) continue;
            out.add(t);
        }
        return out;
    }

    private boolean isPrimitiveName(String t) {
        return "boolean".equals(t) || "byte".equals(t) || "short".equals(t) || "char".equals(t)
                || "int".equals(t) || "long".equals(t) || "float".equals(t) || "double".equals(t);
    }

    private String buildPathKey(Deque<MethodSignature> stack) {
        StringBuilder sb = new StringBuilder();
        boolean first = true;
        for (MethodSignature ms : stack) {
            if (!first) sb.append("->");
            first = false;
            sb.append(buildKey(ms));
        }
        return sb.toString();
    }

    private String formatSignature(MethodSignature ms) {
    String sub = ms.getSubSignature().toString();
        int spaceIdx = sub.indexOf(' ');
        String ret = spaceIdx > 0 ? sub.substring(0, spaceIdx) : "";
        String rest = spaceIdx > 0 ? sub.substring(spaceIdx + 1) : sub;
        String visibility = visibilityOf(ms);
    return ms.getDeclClassType().getFullyQualifiedName() + "#" + rest + ": " + ret + (visibility.isEmpty() ? "" : " (" + visibility + ")");
    }

    private String visibilityOf(MethodSignature ms) {
        try {
            return resolveModifier(ms);
        } catch (Exception e) {
            return "";
        }
    }

    private String resolveModifier(MethodSignature ms) {
        if (modifierCache.containsKey(ms)) return modifierCache.get(ms);
        String key = buildKey(ms);
        String mod = methodModifiers.getOrDefault(key, "");
        modifierCache.put(ms, mod);
        return mod;
    }

    private final Map<String, String> methodModifiers = new HashMap<>();
    private final Map<MethodSignature, String> modifierCache = new HashMap<>();
    private final Map<String, String> classModifiers = new HashMap<>();
    private final Map<String, List<String>> constructorsByClass = new HashMap<>();
    private final Map<String, List<String>> constructorModsByClass = new HashMap<>();
    private final Map<String, List<String>> implementationsOf = new HashMap<>();
    private final Map<String, List<String>> factoryMethodsFor = new HashMap<>();

    private String buildKey(MethodSignature ms) {
        return ms.getDeclClassType().getFullyQualifiedName() + "::" + ms.getSubSignature().toString();
    }

    private String annotateParamModifiers(String paramsCsv) {
        if (paramsCsv == null || paramsCsv.isEmpty()) return "";
        String[] parts = paramsCsv.split(",");
        List<String> out = new ArrayList<>(parts.length);
        for (String p : parts) {
            String t = p.trim();
            if (t.isEmpty()) { out.add(t); continue; }
            String base = t;
            String arraySuffix = "";
            while (base.endsWith("[]")) {
                arraySuffix += "[]";
                base = base.substring(0, base.length() - 2);
            }
            String mod = classModifiers.getOrDefault(base, "");
            if (!mod.isEmpty()) {
                out.add(base + " (" + mod + ")" + arraySuffix);
            } else {
                out.add(t);
            }
        }
        return String.join(", ", out);
    }

    private String computeProjectRootPrefix(String classFqn) {
        if (classFqn == null) return "";
        int lastDot = classFqn.lastIndexOf('.');
        String pkg = lastDot > 0 ? classFqn.substring(0, lastDot) : "";
        if (pkg.isEmpty()) return "";
        String[] segs = pkg.split("\\.");
        if (segs.length <= 2) return pkg;
        StringBuilder root = new StringBuilder();
        int take = Math.min(3, segs.length);
        for (int i = 0; i < take; i++) {
            if (i > 0) root.append('.');
            root.append(segs[i]);
        }
        return root.toString();
    }
    private boolean hasConcreteImplementation(String abstractType, Set<String> visited) {
        if (visited.contains(abstractType)) {
            return false; 
        }
        visited.add(abstractType);
        
        List<String> impls = implementationsOf.getOrDefault(abstractType, Collections.emptyList());
        for (String impl : impls) {
            String implMod = classModifiers.getOrDefault(impl, "").trim();
            if (implMod.startsWith("public") && !implMod.contains("abstract")) {
                return true; 
            }
            if (implMod.contains("abstract")) {
                if (hasConcreteImplementation(impl, visited)) {
                    return true;
                }
            }
        }
        return false;
    }
    private void collectAllImplementations(String type, Set<String> result, Set<String> visited) {
        if (visited.contains(type)) {
            return;
        }
        visited.add(type);
        List<String> impls = implementationsOf.getOrDefault(type, Collections.emptyList());
        for (String impl : impls) {
            String implMod = classModifiers.getOrDefault(impl, "").trim();
            if (implMod.startsWith("public") && !implMod.contains("abstract")) {
                result.add(impl);
            }
            collectAllImplementations(impl, result, visited);
        }
    }
}
