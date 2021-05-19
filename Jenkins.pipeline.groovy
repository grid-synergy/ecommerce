// ----------------------------------------------------------------------------
// written by:  Lawrence McDaniel
//              lpm0073@gmail.com
//              https://lawrencemcdaniel.com
//
// usage:       Base Jenkins pipeline groovy script for build, test, deploy
//              Called by JenkinsFile
//
//              Jenkins host: https://jenkins.gsedxlms.com/
//
//  https://jenkins.gsedxlms.com/job/edx-platform-pipeline/job/gs%252Fkoa.master/pipeline-syntax/html
//  setGitHubPullRequestStatus()
//
// ----------------------------------------------------------------------------

// returns a list of changed files
// see: https://stackoverflow.com/questions/54175878/which-jenkins-command-to-get-the-list-of-changed-files
@NonCPS
String getChangedFilesList() {

    changedFiles = []
    for (changeLogSet in currentBuild.changeSets) { 
        for (entry in changeLogSet.getItems()) { // for each commit in the detected changes
            for (file in entry.getAffectedFiles()) {
                changedFiles.add(file.getPath()) // add changed file to list
            }
        }
    }

    return changedFiles

}

// true if the branch name begins with "gs/" and there are code modifications.
def isGSBranch() {
    return env.BRANCH_NAME.startsWith('gs/')
}
def isGSContractorBranch() {
    return env.BRANCH_NAME.startsWith('gs/crontractor/')
}
def isLhubBranch() {
    return env.BRANCH_NAME.startsWith('lhub/')
}
def isProductionBranch() {
    return env.BRANCH_NAME == 'gs/koa.master'
}

String getGitHubMetadata() {

    def metaData = "Jenkins Build URL: ${BUILD_URL}\n"

    metaData = metaData + "Jenkins Job URL: ${JOB_URL}\n"
    metaData = metaData + "Git repository: ${GIT_URL}\n"
    metaData = metaData + "Git Branch: ${GIT_BRANCH}\n"
    
    if (isProductionBranch()) {
        metaData = metaData + "This is the production branch\n"
    }
    if (isGSBranch()) {
        metaData = metaData + "This branch is in the Grid Synergy Name Space\n"
    }
    if (isGSContractorBranch()) {
        metaData = metaData + "This is a Grid Synergy contractor branch\n"
    }
    if (isLhubBranch()) {
        metaData = metaData + "This branch is in the LHUB Name Space\n"
    }

    if (env.CHANGE_AUTHOR) {metaData = metaData + "Git Pull author: ${CHANGE_AUTHOR}\n"}
    if (env.CHANGE_ID) {metaData = metaData + "Git Pull request: ${CHANGE_ID}\n"}
    if (env.CHANGE_TARGET) {metaData = metaData + "Git Pull branch target: ${CHANGE_TARGET}\n"}
    
    metaData = metaData + "Git Commit: ${GIT_COMMIT}\n"
    metaData = metaData + "Git Commit Message: ${GIT_COMMIT_MSG}\n"
    metaData = metaData + "Git Build Number: ${BUILD_NUMBER}\n"
    if (env.GIT_COMMITTER_NAME) {
            metaData = metaData + "Git committer: ${GIT_COMMITTER_NAME} ${GIT_COMMITTER_EMAIL}\n"
        }
    
    if (env.GIT_AUTHOR_NAME) {
        metaData = metaData + "Git author: ${GIT_AUTHOR_NAME} ${GIT_AUTHOR_EMAIL}\n"
    }

    metaData = metaData + "\n"
    //echo "Initializing Jenkins for version ${NEW_VERSION}"
    
    metaData = metaData + "I harken from Jenkins.pipeline.groovy in the root folder of this git repository\n"
    metaData = metaData + "Git changed files list: ${changedFiles}\n"

    metaData = metaData + "\n"
    metaData = metaData + "Jenkins environment variables:\n"
    metaData = metaData + "------------------------------\n"
    metaData = metaData + "\n"
    metaData = metaData + "BRANCH_NAME: ${BRANCH_NAME}\n"

    if (env.CHANGE_ID) {
        metaData = metaData + "optional Pull request variables\n"
        metaData = metaData + "CHANGE_ID: ${CHANGE_ID}\n"
        metaData = metaData + "CHANGE_URL ${CHANGE_URL}\n"
        metaData = metaData + "CHANGE_TITLE ${CHANGE_TITLE}\n"
        metaData = metaData + "CHANGE_AUTHOR ${CHANGE_AUTHOR}\n"
        metaData = metaData + "CHANGE_AUTHOR_DISPLAY_NAME ${CHANGE_AUTHOR_DISPLAY_NAME}\n"
        metaData = metaData + "CHANGE_AUTHOR_EMAIL ${CHANGE_AUTHOR_EMAIL}\n"
        metaData = metaData + "CHANGE_TARGET ${CHANGE_TARGET}\n"
        metaData = metaData + "CHANGE_BRANCH ${CHANGE_BRANCH}\n"
        metaData = metaData + "CHANGE_FORK ${CHANGE_FORK}\n"
    }

    if (env.TAG_NAME) {
        metaData = metaData + 'optional Git Tag variables'
        metaData = metaData + "TAG_NAME ${TAG_NAME}\n"
        metaData = metaData + "TAG_TIMESTAMP ${TAG_TIMESTAMP}\n"
        metaData = metaData + "TAG_UNIXTIME ${TAG_UNIXTIME}\n"
        metaData = metaData + "TAG_DATE ${TAG_DATE}\n"
    }

    
    if (env.BUILD_NUMBER) {metaData = metaData + "BUILD_NUMBER ${BUILD_NUMBER}\n"}
    if (env.BUILD_ID) {metaData = metaData + "BUILD_ID ${BUILD_ID}\n"}
    if (env.BUILD_DISPLAY_NAME) {metaData = metaData + "BUILD_DISPLAY_NAME ${BUILD_DISPLAY_NAME}\n"}
    if (env.BUILD_TAG) {metaData = metaData + "BUILD_TAG ${BUILD_TAG}\n"}
    if (env.BUILD_URL) {metaData = metaData + "BUILD_URL ${BUILD_URL}\n"}

    if (env.JOB_NAME) {metaData = metaData + "JOB_NAME ${JOB_NAME}\n"}
    if (env.JOB_BASE_NAME) {metaData = metaData + "JOB_BASE_NAME ${JOB_BASE_NAME}\n"}
    if (env.JOB_URL) {metaData = metaData + "JOB_URL ${JOB_URL}\n"}

    if (env.EXECUTOR_NUMBER) {metaData = metaData + "EXECUTOR_NUMBER ${EXECUTOR_NUMBER}\n"}
    if (env.NODE_NAME) {metaData = metaData + "NODE_NAME ${NODE_NAME}\n"}
    if (env.NODE_LABELS) {metaData = metaData + "NODE_LABELS ${NODE_LABELS}\n"}
    if (env.WORKSPACE) {metaData = metaData + "WORKSPACE ${WORKSPACE}\n"}
    if (env.WORKSPACE_TMP) {metaData = metaData + "WORKSPACE_TMP ${WORKSPACE_TMP}\n"}
    if (env.JENKINS_HOME) {metaData = metaData + "JENKINS_HOME ${JENKINS_HOME}\n"}
    if (env.JENKINS_URL) {metaData = metaData + "JENKINS_URL ${JENKINS_URL}\n"}

    if (env.GIT_COMMIT) {metaData = metaData + "GIT_COMMIT ${GIT_COMMIT}\n"}
    if (env.GIT_PREVIOUS_COMMIT) {metaData = metaData + "GIT_PREVIOUS_COMMIT ${GIT_PREVIOUS_COMMIT}\n"}
    if (env.GIT_PREVIOUS_SUCCESSFUL_COMMIT) {metaData = metaData + "GIT_PREVIOUS_SUCCESSFUL_COMMIT ${GIT_PREVIOUS_SUCCESSFUL_COMMIT}\n"}
    if (env.GIT_BRANCH) {metaData = metaData + "GIT_BRANCH ${GIT_BRANCH}\n"}
    if (env.GIT_LOCAL_BRANCH) {metaData = metaData + "GIT_LOCAL_BRANCH ${GIT_LOCAL_BRANCH}\n"}
    if (env.GIT_CHECKOUT_DIR) {metaData = metaData + "GIT_CHECKOUT_DIR ${GIT_CHECKOUT_DIR}\n"}
    if (env.GIT_URL) {metaData = metaData + "GIT_URL ${GIT_URL}\n"}
    if (env.GIT_COMMITTER_NAME) {metaData = metaData + "GIT_COMMITTER_NAME ${GIT_COMMITTER_NAME}\n"}
    if (env.GIT_AUTHOR_NAME) {metaData = metaData + "GIT_AUTHOR_NAME ${GIT_AUTHOR_NAME}\n"}
    if (env.GIT_COMMITTER_EMAIL) {metaData = metaData + "GIT_COMMITTER_EMAIL ${GIT_COMMITTER_EMAIL}\n"}
    if (env.GIT_AUTHOR_EMAIL) {metaData = metaData + "GIT_AUTHOR_EMAIL ${GIT_AUTHOR_EMAIL}\n"}

    metaData = metaData + "\n"
    metaData = metaData + "\n"
    return metaData
}

def initEnvironment() {

    changedFiles = getChangedFilesList()

    echo 'Initializing Jenkins environment...'
    env.GIT_COMMIT_MSG = sh (script: 'git log -1 --pretty=%B ${GIT_COMMIT}', returnStdout: true).trim()
    echo getGitHubMetadata()

}

def buildApp() {


    // see notes in testApp

    echo 'Building edx-platform...'
    sh 'python --version'
    sh 'expr 1 + 0'

}

def testApp() {

    echo 'Testing edx-platform...'
    sh 'python --version'

    // a couple of choices for this:
    // 1. run tests on a remote EC2 instance, initiated by calling a bash script.
    // 2. run tests on this EC2 instance.

}

def deployApp() {

    echo 'Deploying edx-platform...'
    sh 'python --version'
    //echo "Using ssh key ${SSH_KEY}"
    //echo "Deploying version ${params.VERSION}"

    if (env.CHANGE_ID) {
        // This is currently the best way to push a tag (or a branch, etc) from a
        // Pipeline job. It's not ideal - https://issues.jenkins-ci.org/browse/JENKINS-28335
        // is an open JIRA for getting the GitPublisher Jenkins functionality working
        // with Pipeline.



        // For SSH private key authentication, try the sshagent step from the SSH Agent plugin.
        //sshagent (credentials: ['git-ssh-credentials-ID']) {
        //    sh("git tag -a some_tag -m 'Jenkins'")
        //    sh('git push <REPO> --tags')
        //
        //}

        echo 'This is a pull request. Tests succeeded, so we will merge this code to koa.master'

        // credentialsId here is the credentials you have set up in Jenkins for pushing
        // to that repository using username and password.
        //withCredentials([usernamePassword(credentialsId: 'cd31dbc2-0825-40d7-ab0d-9bd198538162', passwordVariable: 'GIT_PASSWORD', usernameVariable: 'GIT_USERNAME')]) {
        //    sh("git tag -a some_tag -m 'Jenkins'")
        //    sh('git push https://${GIT_USERNAME}:${GIT_PASSWORD}@<REPO> --tags')
        //}

    } else {
        echo 'This is not a pull request. nothing more to do, even though tests succeeded.'
    }

}


return this