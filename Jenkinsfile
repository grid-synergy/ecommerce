// ----------------------------------------------------------------------------
// written by:  Lawrence McDaniel
//              lpm0073@gmail.com
//              https://lawrencemcdaniel.com
//
// usage:       Base Jenkins pipeline script to build, test, 
//              merge to koa.master.
//
//              Jenkins host: https://jenkins.gsedxlms.com/
//
//              Jenkins variables: https://jenkins.gsedxlms.com/env-vars.html/
// webhook test #7
// ----------------------------------------------------------------------------
def gv 

pipeline {

    agent { docker { image 'python:3.5.1' } }
    //agent any 

    // +++++++++++++++++++++++++++++++++++++++++++++++++++++++
    // I. itemized build stages for init, build, test, deploy
    // +++++++++++++++++++++++++++++++++++++++++++++++++++++++

    stages {

        stage("init") {

            steps {
                script {
                    gv = load "Jenkins.pipeline.groovy"
                    gv.initEnvironment()

                    //def email_subject = "Jenkins build ${BUILD_ID}: ${GIT_BRANCH} in ${GIT_URL}"
                    //def email_body = gv.getGitHubMetadata()
                    //def email_providers = [ [$class: 'CulpritsRecipientProvider'], [$class: 'DevelopersRecipientProvider'] ];

                    //email_providers.add ( [$class: 'RequesterRecipientProvider'] );

                    //emailext (
                    //    to: 'andrew@gridsynergy.com.sg',
                    //    recipientProviders: email_providers,
                    //    subject: email_subject,
                    //    attachLog: true,
                    //    body: email_body
                    //)
                }
            }

        }

        stage('build') {

            steps {
                script {
                    if (gv.isGSBranch()) {
                        echo 'this is a gs/ branch: building'
                    } else {
                        echo 'this is not a gs/ branch but we will build it anyway'
                    }
                    gv.buildApp()
                }
            }

        }

        stage("test") {

            steps {
                script {
                    if (gv.isGSBranch()) {
                        echo 'this is a gs/ branch: testing'
                    } else {
                        echo 'this is not a gs/ branch but we will test anyway'
                    }
                    gv.testApp()
                }
            }

        }

        stage("deploy") {

            steps {

                script {
                    if (gv.isGSBranch()) {
                        gv.deployApp()
                    } else {
                        echo 'this is not a gs/ branch. not deploying'
                    }
                }

                // requires plugins: Credentials, Credentials Binding
                //withCredentials([
                //    usernamePassword(
                //        credentials: 'gs-edx-staging', 
                //        usernameVariable: USER, 
                //        passwordVariable: PWD)
                //]) {
                //        // user, pwd available here.
                //        echo "username is ${USER}."
                //}
            }

        }        

    }

    // +++++++++++++++++++++++++++++++++++++++++++++++++++++++
    // II. conditional processing that we add after the pipeline
    //     has executed. we can differentiate between
    //     build success, failure, or a change in state 
    //     (i.e. builds had been successful but this build failed.)
    // +++++++++++++++++++++++++++++++++++++++++++++++++++++++
   post {

        always {

            echo 'Cleaning up Jenkins environment...'

            // email results to the committers
            script {
                emailext subject: '$DEFAULT_SUBJECT',
                    body: '$DEFAULT_CONTENT',
                    recipientProviders: [
                        [$class: 'DevelopersRecipientProvider'],
                        [$class: 'RequesterRecipientProvider']
                    ], 
                    replyTo: '$DEFAULT_REPLYTO',
                    attachLog: true,
                    to: '$DEFAULT_RECIPIENTS'
            }

        }

        failure {
            
            echo 'Jenkins post - Failure...'

        }

        success {
            echo 'Jenkins post - Success...'
            script {
                if (gv.isProductionBranch()) {
                    // announce on Slack.
                    echo "This pull request / commit merged to production branch."
                    slackSend channel: '#codeissues', color: 'good', message: "Commit to production branch ${currentBuild.fullDisplayName}\nCommit hash: ${GIT_COMMIT}\nCommit message: ${GIT_COMMIT_MSG}\nCommitted by ${GIT_COMMITTER_NAME} ${GIT_COMMITTER_EMAIL}\nFiles affected by this commit: ${gv.getChangedFilesList()}"
                    slackSend channel: '#codeissues', color: 'good', message: "Additional details about this build and the pipeline build log are available here: ${JOB_URL}"
                }
            }

        }

        changed {
            script {
                // email our culprits that the state has changed.
                emailext subject: '$DEFAULT_SUBJECT',
                    body: '$DEFAULT_CONTENT',
                    recipientProviders: [[$class: 'CulpritsRecipientProvider']], 
                    replyTo: '$DEFAULT_REPLYTO',
                    attachLog: true,
                    to: 'andrew@gridsynergy.com.sg, lpm0073@gmail.com'

                if (gv.isProductionBranch()) {
                    if (currentBuild.currentResult == 'SUCCESS') { // Other values: SUCCESS, UNSTABLE
                        slackSend channel: '#codeissues', color: 'good', message: "Pipeline for ${currentBuild.fullDisplayName} has stabilized. More info: ${JOB_URL}"
                    }
                    if (currentBuild.currentResult == 'FAILURE') { // Other values: SUCCESS, UNSTABLE
                        slackSend channel: '#codeissues', color: 'bad', message: "Build pipeline ${currentBuild.fullDisplayName} failed. More info: ${JOB_URL}"
                    }
                    if (currentBuild.currentResult == 'UNSTABLE') { // Other values: SUCCESS, UNSTABLE
                        slackSend channel: '#codeissues', color: 'bad', message: "Build pipeline ${currentBuild.fullDisplayName} is unstable. More info: ${JOB_URL}"
                    }
                }

            }
        }


    }    

}